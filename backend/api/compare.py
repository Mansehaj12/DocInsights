"""
Multi-document comparison API routes.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.document import Document, DocumentStatus
from backend.models.insight import DocumentInsight, InsightType
from backend.models.schemas import CompareRequest, CompareResponse
from backend.services.llm_client import LLMError
from backend.services.rag_service import compare_documents
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["Compare"])


@router.post("/compare", response_model=CompareResponse)
async def compare_docs(request: CompareRequest, db: AsyncSession = Depends(get_db)):
    """
    Compare multiple documents and identify similarities and differences.
    """
    # Fetch all documents
    result = await db.execute(
        select(Document).filter(Document.id.in_(request.document_ids))
    )
    docs = result.scalars().all()
    
    if len(docs) != len(request.document_ids):
        raise HTTPException(status_code=404, detail="One or more documents not found")
    
    # Verify all are ready
    for doc in docs:
        if doc.status != DocumentStatus.READY:
            raise HTTPException(
                status_code=400,
                detail=f"Document '{doc.original_filename}' is not ready. Status: {doc.status}"
            )
    
    # Build document data for comparison
    doc_data = [
        {"id": d.id, "filename": d.original_filename, "text": d.text_content}
        for d in docs
    ]
    
    logger.info("compare_request", doc_ids=request.document_ids)

    # Compare
    try:
        comparison = compare_documents(doc_data)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    
    # Save insight for each document
    for doc in docs:
        insight = DocumentInsight(
            document_id=doc.id,
            insight_type=InsightType.COMPARISON,
            content_json=json.dumps(comparison),
        )
        db.add(insight)
    
    return CompareResponse(
        document_ids=request.document_ids,
        similarities=comparison.get("similarities", []),
        differences=comparison.get("differences", []),
        summary=comparison.get("summary", ""),
    )
