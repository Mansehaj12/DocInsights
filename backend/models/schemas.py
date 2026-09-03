from typing import Optional, Union, List, Dict, Any
"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ============================================
# Enums (mirroring DB enums for API layer)
# ============================================

class DocumentStatusEnum(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class InsightTypeEnum(str, Enum):
    SUMMARY = "summary"
    EXTRACTION = "extraction"
    RISK = "risk"
    COMPARISON = "comparison"
    HIGHLIGHTS = "highlights"


class DocumentTypeEnum(str, Enum):
    """Document category for specialized extraction."""
    LEGAL = "legal"
    FINANCIAL = "financial"
    RESEARCH = "research"
    GENERAL = "general"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


# ============================================
# Document Schemas
# ============================================

class DocumentResponse(BaseModel):
    """Response schema for a single document."""
    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: DocumentStatusEnum
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response schema for document listing."""
    documents: list[DocumentResponse]
    total: int


class DocumentStatusResponse(BaseModel):
    """Simple status response for a document."""
    id: int
    status: DocumentStatusEnum
    error_message: Optional[str] = None


# ============================================
# Search Schemas
# ============================================

class SearchRequest(BaseModel):
    """Request to perform semantic search."""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    document_id: Optional[int] = Field(default=None, description="Restrict search to a specific document")


class SearchResult(BaseModel):
    """A single search result."""
    chunk_id: int
    document_id: int
    document_name: str
    content: str
    score: float
    page: Optional[int] = None


class SearchResponse(BaseModel):
    """Response for a search query."""
    query: str
    results: list[SearchResult]
    total: int


# ============================================
# Chat Schemas
# ============================================

class ChatRequest(BaseModel):
    """Request to chat with a document."""
    question: str = Field(..., min_length=1, max_length=2000, description="Question to ask")


class ChatSource(BaseModel):
    """A cited source from the document."""
    chunk_index: int
    content: str
    page: Optional[int] = None
    relevance_score: float


class HighlightItem(BaseModel):
    """Evidence highlight with precise text location for frontend rendering."""
    document_id: int
    page_number: Optional[int] = None
    chunk_index: int
    text: str
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    relevance_score: float = 0.0


class ChatResponse(BaseModel):
    """Response from document chat."""
    answer: str
    sources: list[ChatSource]
    document_id: int
    highlights: list[HighlightItem] = []  # NEW — defaults to [] for backward compat


class ChatHistoryResponse(BaseModel):
    """Chat history for a document."""
    messages: list[dict]
    document_id: int


# ============================================
# Insight Schemas
# ============================================

class SummaryResponse(BaseModel):
    """AI-generated document summary."""
    document_id: int
    executive_summary: str
    section_summaries: list[dict]
    bullet_highlights: list[str]
    key_takeaways: list[str]


class ExtractionRequest(BaseModel):
    """Request for key info extraction."""
    document_type: DocumentTypeEnum = Field(default=DocumentTypeEnum.GENERAL, description="Document type for specialized extraction")


class ExtractionResponse(BaseModel):
    """Extracted key information."""
    document_id: int
    document_type: str
    extracted_data: dict


class RiskItem(BaseModel):
    """A single risk finding."""
    risk_type: str
    severity: RiskLevel
    description: str
    highlighted_text: str
    recommendation: Optional[str] = None


class RiskResponse(BaseModel):
    """Risk detection results."""
    document_id: int
    overall_risk_score: RiskLevel
    risk_items: list[RiskItem]
    total_risks: int


# ============================================
# Comparison Schemas
# ============================================

class CompareRequest(BaseModel):
    """Request to compare multiple documents."""
    document_ids: list[int] = Field(..., min_length=2, max_length=5, description="IDs of documents to compare")
    comparison_type: str = Field(default="general", description="Type: general, clauses, financial, research")


class ComparisonDifference(BaseModel):
    """A single difference between documents."""
    category: str
    document_a: str
    document_b: str
    detail: str


class CompareResponse(BaseModel):
    """Comparison results."""
    document_ids: list[int]
    similarities: list[str]
    differences: list[ComparisonDifference]
    summary: str


# ============================================
# Dashboard Schemas
# ============================================

class DashboardStats(BaseModel):
    """Aggregate dashboard statistics."""
    total_documents: int
    documents_by_status: dict[str, int]
    documents_by_type: dict[str, int]
    total_risks: int
    risk_distribution: dict[str, int]
    recent_documents: list[DocumentResponse]


class TimelineEvent(BaseModel):
    """A timeline event (deadline, date, etc.)."""
    date: str
    description: str
    document_id: int
    document_name: str
    event_type: str


# ============================================
# Multi-Document Chat Schemas
# ============================================

class MultiChatRequest(BaseModel):
    """Request to chat across multiple documents."""
    document_ids: list[int] = Field(..., min_length=2, max_length=5, description="IDs of documents to chat across")
    question: str = Field(..., min_length=1, max_length=2000, description="Question to ask")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve per document")


class MultiChatSource(BaseModel):
    """A source from multi-document chat with document attribution."""
    chunk_id: int
    document_id: int
    document_name: str
    chunk_index: int
    content: str
    relevance_score: float


class DocumentGroup(BaseModel):
    """Sources grouped by document."""
    document_id: int
    document_name: str
    sources: list[MultiChatSource]


class MultiChatResponse(BaseModel):
    """Response from multi-document chat."""
    answer: str
    sources: list[MultiChatSource]
    highlights: list[HighlightItem] = []
    document_groups: list[DocumentGroup] = []
    document_ids: list[int]


# ============================================
# Report Schemas
# ============================================

class ReportRequest(BaseModel):
    """Request to generate a PDF report."""
    document_id: int
    report_type: str = Field(default="comprehensive", description="Report type: comprehensive, summary, risk")

