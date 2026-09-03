"""
Semantic search API routes.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.chunk import DocumentChunk
from backend.models.document import Document
from backend.models.schemas import SearchRequest, SearchResponse, SearchResult
from backend.services.embedding_service import embed_query
from backend.services.vector_store import search as vector_search
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["Search"])


@router.post("/search", response_model=SearchResponse)
async def semantic_search(request: SearchRequest, db: AsyncSession = Depends(get_db)):
    """
    Perform semantic search across all documents (or a specific one).
    Uses embedding similarity via FAISS for fast retrieval.
    """
    logger.info("search_request", query=request.query[:100], top_k=request.top_k)
    
    # Embed query
    query_embedding = embed_query(request.query)
    
    # Search vector store
    results = vector_search(
        query_embedding,
        top_k=request.top_k,
        document_id=request.document_id,
    )
    
    if not results:
        return SearchResponse(query=request.query, results=[], total=0)
    
    # Fetch chunk details from DB
    chunk_ids = [r["chunk_id"] for r in results]
    chunk_result = await db.execute(
        select(DocumentChunk).filter(DocumentChunk.id.in_(chunk_ids))
    )
    chunks = {c.id: c for c in chunk_result.scalars().all()}
    
    # Fetch document names
    doc_ids = list(set(r["document_id"] for r in results))
    doc_result = await db.execute(
        select(Document).filter(Document.id.in_(doc_ids))
    )
    docs = {d.id: d for d in doc_result.scalars().all()}
    
    # Build response
    search_results = []
    for r in results:
        chunk = chunks.get(r["chunk_id"])
        doc = docs.get(r["document_id"])
        if chunk and doc:
            search_results.append(SearchResult(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                document_name=doc.original_filename,
                content=chunk.content,
                score=r["score"],
                page=chunk.start_page,
            ))
    
    return SearchResponse(
        query=request.query,
        results=search_results,
        total=len(search_results),
    )


@router.post("/documents/{document_id}/search", response_model=SearchResponse)
async def search_within_document(
    document_id: int,
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Search within a specific document."""
    # Verify document exists
    result = await db.execute(select(Document).filter(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Override document_id in request
    request.document_id = document_id
    return await semantic_search(request, db)
