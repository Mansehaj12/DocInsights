"""
DocumentInsight model — stores AI-generated insights (summaries, risks, extractions).
"""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class InsightType(str, enum.Enum):
    """Types of AI-generated insights."""
    SUMMARY = "summary"
    EXTRACTION = "extraction"
    RISK = "risk"
    COMPARISON = "comparison"
    HIGHLIGHTS = "highlights"


class DocumentInsight(Base):
    """An AI-generated insight for a document."""
    __tablename__ = "document_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    insight_type = Column(Enum(InsightType), nullable=False)
    content_json = Column(Text, nullable=False)  # JSON string with structured insight data
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="insights")

    def __repr__(self):
        return f"<DocumentInsight(id={self.id}, doc={self.document_id}, type='{self.insight_type}')>"
