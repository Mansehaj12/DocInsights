"""
Chat with documents API routes (RAG-powered Q&A).
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.chat import ChatMessage, MessageRole
from backend.models.chunk import DocumentChunk
from backend.models.document import Document, DocumentStatus
from backend.models.schemas import ChatHistoryResponse, ChatRequest, ChatResponse
from backend.services.rag_service import ask_question
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/documents", tags=["Chat"])


@router.post("/{document_id}/chat", response_model=ChatResponse)
async def chat_with_document(
    document_id: int,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Ask a question about a document using RAG.
    Retrieves relevant chunks, injects context, and generates a grounded response.
    """
    # Verify document is ready
    result = await db.execute(select(Document).filter(Document.id == document_id))
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != DocumentStatus.READY:
        raise HTTPException(status_code=400, detail=f"Document not ready. Status: {doc.status}")
    
    # Fetch chunks for this document
    chunk_result = await db.execute(
        select(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = chunk_result.scalars().all()
    chunks_data = [
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
    
    # RAG pipeline
    logger.info("chat_request", doc_id=document_id, question=request.question[:100])
    rag_result = ask_question(request.question, document_id, chunks_data)
    
    # Save user message
    user_msg = ChatMessage(
        document_id=document_id,
        role=MessageRole.USER,
        content=request.question,
    )
    db.add(user_msg)
    
    # Save assistant message
    assistant_msg = ChatMessage(
        document_id=document_id,
        role=MessageRole.ASSISTANT,
        content=rag_result["answer"],
        sources_json=json.dumps(rag_result["sources"]),
    )
    db.add(assistant_msg)
    
    return ChatResponse(
        answer=rag_result["answer"],
        sources=rag_result["sources"],
        document_id=document_id,
        highlights=rag_result.get("highlights", []),
    )


@router.get("/{document_id}/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(document_id: int, db: AsyncSession = Depends(get_db)):
    """Get chat history for a document."""
    # Verify document exists
    result = await db.execute(select(Document).filter(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Fetch messages
    result = await db.execute(
        select(ChatMessage)
        .filter(ChatMessage.document_id == document_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    
    formatted = [
        {
            "id": m.id,
            "role": m.role.value,
            "content": m.content,
            "sources": json.loads(m.sources_json) if m.sources_json else None,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]
    
    return ChatHistoryResponse(messages=formatted, document_id=document_id)
