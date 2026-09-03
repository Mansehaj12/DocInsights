"""
Document management API routes.
Upload, list, view, delete documents.
"""

import os
import shutil
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.document import Document, DocumentStatus
from backend.models.chunk import DocumentChunk
from backend.models.schemas import DocumentListResponse, DocumentResponse, DocumentStatusResponse
from backend.utils.file_validator import (
    FileValidationError,
    ensure_upload_dir,
    sanitize_filename,
    validate_file_extension,
    validate_file_size,
    validate_magic_bytes,
)
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document for processing.
    Validates file type, size, and content before saving.
    Triggers async processing if Celery is available, else processes inline.
    """
    try:
        # Validate extension
        file_ext = validate_file_extension(file.filename or "unknown")
        
        # Read file content
        content = await file.read()
        
        # Validate size
        validate_file_size(len(content))
        
        # Validate magic bytes
        validate_magic_bytes(content, file_ext)
        
    except FileValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # Sanitize and create unique filename
    safe_name = sanitize_filename(file.filename or "unnamed")
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    
    # Save file
    upload_dir = ensure_upload_dir()
    file_path = str(upload_dir / unique_name)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create DB record
    doc = Document(
        filename=unique_name,
        original_filename=file.filename or "unnamed",
        file_type=file_ext,
        file_size=len(content),
        file_path=file_path,
        status=DocumentStatus.UPLOADED,
    )
    db.add(doc)
    await db.flush()
    
    logger.info("document_uploaded", doc_id=doc.id, filename=safe_name, size=len(content))

    # Process the document. Inline (synchronous) is the default — no Celery/Redis
    # required, which is what the single-container deployment uses. Celery is only
    # attempted when explicitly enabled (a worker + Redis broker must be running),
    # so we never pay a broker connection timeout just to fall back.
    from backend.config import get_settings
    settings = get_settings()

    if settings.use_celery:
        try:
            from backend.workers.tasks import process_document_task
            process_document_task.delay(doc.id)
            logger.info("processing_queued", doc_id=doc.id)
        except Exception as e:
            # Broker unreachable — degrade gracefully to inline processing.
            logger.warning("celery_unavailable", error=str(e), msg="Processing inline")
            await _process_inline(doc, db)
    else:
        await _process_inline(doc, db)

    return doc


async def _process_inline(doc: Document, db: AsyncSession):
    """Process a document inline when Celery is not available."""
    import asyncio
    from backend.services.document_processor import extract_text
    from backend.services.embedding_service import embed_texts
    from backend.services.vector_store import add_embeddings
    from backend.utils.text_utils import chunk_text
    
    try:
        doc.status = DocumentStatus.PROCESSING
        await db.flush()
        
        # Extract text
        result = extract_text(doc.file_path, doc.file_type)
        doc.text_content = result["text"]
        doc.page_count = result["page_count"]
        doc.word_count = result["word_count"]
        doc.language = result["language"]
        doc.metadata_json = result["metadata_json"]
        
        # Chunk text
        doc.status = DocumentStatus.CHUNKING
        await db.flush()
        
        chunks = chunk_text(result["text"], chunk_size=1000, chunk_overlap=200)
        
        db_chunks = []
        for i, chunk_data in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=i,
                content=chunk_data["content"],
                start_char=chunk_data["start_char"],
                end_char=chunk_data["end_char"],
                token_count=len(chunk_data["content"].split()),
            )
            db.add(chunk)
            db_chunks.append(chunk)
        
        await db.flush()
        
        # Generate embeddings
        doc.status = DocumentStatus.EMBEDDING
        await db.flush()
        
        chunk_texts = [c.content for c in db_chunks]
        embeddings = embed_texts(chunk_texts)
        
        # Index in FAISS
        chunk_ids = [c.id for c in db_chunks]
        chunk_indices = [c.chunk_index for c in db_chunks]
        add_embeddings(doc.id, chunk_ids, chunk_indices, embeddings)
        
        doc.status = DocumentStatus.READY
        doc.updated_at = datetime.utcnow()
        
        logger.info("inline_processing_complete", doc_id=doc.id)
        
    except Exception as e:
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(e)
        logger.error("inline_processing_failed", doc_id=doc.id, error=str(e))


@router.get("", response_model=DocumentListResponse)
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all documents with their processing status."""
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed information about a specific document."""
    result = await db.execute(select(Document).filter(Document.id == document_id))
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return doc


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(document_id: int, db: AsyncSession = Depends(get_db)):
    """Get the processing status of a document."""
    result = await db.execute(select(Document).filter(Document.id == document_id))
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentStatusResponse(id=doc.id, status=doc.status, error_message=doc.error_message)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a document and all its associated data."""
    result = await db.execute(select(Document).filter(Document.id == document_id))
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file from disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    
    # Delete from vector store
    from backend.services.vector_store import delete_document_embeddings
    delete_document_embeddings(document_id)
    
    # Delete from DB (cascades to chunks, insights, messages)
    await db.delete(doc)
    
    logger.info("document_deleted", doc_id=document_id)


@router.get("/{document_id}/text")
async def get_document_text(document_id: int, db: AsyncSession = Depends(get_db)):
    """Get the extracted text content of a document."""
    result = await db.execute(select(Document).filter(Document.id == document_id))
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.status != DocumentStatus.READY:
        raise HTTPException(status_code=400, detail=f"Document is not ready. Status: {doc.status}")
    
    return {
        "document_id": doc.id,
        "text": doc.text_content,
        "page_count": doc.page_count,
        "word_count": doc.word_count,
    }
