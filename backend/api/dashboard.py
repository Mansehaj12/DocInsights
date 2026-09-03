"""
Dashboard analytics API routes.
"""

import json
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.document import Document, DocumentStatus
from backend.models.insight import DocumentInsight, InsightType
from backend.models.schemas import DashboardStats, DocumentResponse
from backend.services.vector_store import get_index_stats
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get aggregate dashboard statistics."""
    # Total documents
    result = await db.execute(select(func.count(Document.id)))
    total_docs = result.scalar() or 0
    
    # Documents by status
    result = await db.execute(
        select(Document.status, func.count(Document.id)).group_by(Document.status)
    )
    status_counts = {row[0].value if hasattr(row[0], 'value') else str(row[0]): row[1] for row in result.all()}
    
    # Documents by type
    result = await db.execute(
        select(Document.file_type, func.count(Document.id)).group_by(Document.file_type)
    )
    type_counts = {row[0]: row[1] for row in result.all()}
    
    # Risk analysis
    result = await db.execute(
        select(DocumentInsight)
        .filter(DocumentInsight.insight_type == InsightType.RISK)
    )
    risk_insights = result.scalars().all()
    
    risk_distribution = Counter()
    total_risks = 0
    for insight in risk_insights:
        try:
            data = json.loads(insight.content_json)
            risk_items = data.get("risk_items", [])
            total_risks += len(risk_items)
            for item in risk_items:
                severity = item.get("severity", "Medium")
                risk_distribution[severity] += 1
        except (json.JSONDecodeError, AttributeError):
            pass
    
    # Recent documents
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc()).limit(5)
    )
    recent_docs = [DocumentResponse.model_validate(d) for d in result.scalars().all()]
    
    return DashboardStats(
        total_documents=total_docs,
        documents_by_status=status_counts,
        documents_by_type=type_counts,
        total_risks=total_risks,
        risk_distribution=dict(risk_distribution),
        recent_documents=recent_docs,
    )


@router.get("/risks")
async def get_risk_overview(db: AsyncSession = Depends(get_db)):
    """Get risk scores across all documents."""
    result = await db.execute(
        select(DocumentInsight, Document)
        .join(Document)
        .filter(DocumentInsight.insight_type == InsightType.RISK)
        .order_by(DocumentInsight.created_at.desc())
    )
    
    risks = []
    for insight, doc in result.all():
        try:
            data = json.loads(insight.content_json)
            risks.append({
                "document_id": doc.id,
                "document_name": doc.original_filename,
                "overall_risk_score": data.get("overall_risk_score", "Unknown"),
                "risk_count": len(data.get("risk_items", [])),
                "risk_items": data.get("risk_items", [])[:3],  # Top 3 risks
                "analyzed_at": insight.created_at.isoformat(),
            })
        except json.JSONDecodeError:
            pass
    
    return {"risks": risks, "total": len(risks)}


@router.get("/timeline")
async def get_timeline(db: AsyncSession = Depends(get_db)):
    """Get timeline of document events (deadlines, dates extracted)."""
    result = await db.execute(
        select(DocumentInsight, Document)
        .join(Document)
        .filter(DocumentInsight.insight_type == InsightType.EXTRACTION)
        .order_by(DocumentInsight.created_at.desc())
    )
    
    events = []
    for insight, doc in result.all():
        try:
            data = json.loads(insight.content_json)
            deadlines = data.get("deadlines", [])
            for deadline in deadlines:
                events.append({
                    "date": deadline if isinstance(deadline, str) else str(deadline),
                    "description": f"Deadline from {doc.original_filename}",
                    "document_id": doc.id,
                    "document_name": doc.original_filename,
                    "event_type": "deadline",
                })
        except json.JSONDecodeError:
            pass
    
    return {"events": events, "total": len(events)}


@router.get("/vector-stats")
async def get_vector_store_stats():
    """Get statistics about the vector store."""
    stats = get_index_stats()
    return stats
