"""
ChatMessage model — stores RAG conversation history.
"""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class MessageRole(str, enum.Enum):
    """Role of a chat message."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(Base):
    """A message in a document chat conversation."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    sources_json = Column(Text, nullable=True)  # JSON: cited chunk sources
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, doc={self.document_id}, role='{self.role}')>"
