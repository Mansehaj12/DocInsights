"""
Multi-document chat API routes (v2).
POST /api/chat/multi — chat across multiple documents simultaneously.
Isolated from existing chat.py — no breaking changes.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_db
from backend.models.chunk import DocumentChunk
from backend.models.document import Document, DocumentStatus
from backend.models.schemas import MultiChatRequest, MultiChatResponse
from backend.services.rag_service_v2 import ask_multi_document
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Multi-Document Chat"])


@router.post("/multi", response_model=MultiChatResponse)
async def multi_document_chat(
    request: MultiChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Chat across multiple documents simultaneously.
    Uses RAG v2 pipeline with bounded retrieval, per-doc caps,
    token-aware context, and timeout-safe LLM calls.
    """
    settings = get_settings()

    # Feature flag
    if not settings.enable_multi_doc_chat:
        raise HTTPException(
            status_code=403,
            detail="Multi-document chat is currently disabled",
        )

    if len(request.document_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 documents required")
    if len(request.document_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 documents allowed")

    # Validate all documents exist and are READY
    result = await db.execute(
        select(Document).filter(Document.id.in_(request.document_ids))
    )
    docs = {d.id: d for d in result.scalars().all()}

    if len(docs) != len(request.document_ids):
        missing = set(request.document_ids) - set(docs.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Documents not found: {missing}",
        )

    for doc_id, doc in docs.items():
        if doc.status != DocumentStatus.READY:
            raise HTTPException(
                status_code=400,
                detail=f"Document '{doc.original_filename}' not ready (status: {doc.status})",
            )

    # Fetch chunks for all documents
    chunks_by_doc = {}
    doc_names = {}
    for doc_id, doc in docs.items():
        chunk_result = await db.execute(
            select(DocumentChunk)
            .filter(DocumentChunk.document_id == doc_id)
            .order_by(DocumentChunk.chunk_index)
        )
        chunks = chunk_result.scalars().all()
        chunks_by_doc[doc_id] = [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "content": c.content,
                "start_page": c.start_page,
                "start_char": c.start_char,
                "end_char": c.end_char,
            }
            for c in chunks
        ]
        doc_names[doc_id] = doc.original_filename

    # RAG v2 pipeline
    logger.info(
        "multi_chat_request",
        document_ids=request.document_ids,
        question=request.question[:100],
    )

    rag_result = ask_multi_document(
        question=request.question,
        document_ids=request.document_ids,
        chunks_by_doc=chunks_by_doc,
        doc_names=doc_names,
        top_k=request.top_k,
    )

    return MultiChatResponse(
        answer=rag_result["answer"],
        sources=rag_result["sources"],
        highlights=rag_result.get("highlights", []),
        document_groups=rag_result.get("document_groups", []),
        document_ids=request.document_ids,
    )
