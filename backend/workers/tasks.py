"""
Celery background tasks for document processing, embedding, and insight generation.
"""

import json
import asyncio
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import get_settings
from backend.workers.celery_app import celery_app
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)

# Sync DB engine for Celery workers (Celery doesn't support async)
settings = get_settings()
_sync_db_url = settings.database_url.replace("+aiosqlite", "").replace("sqlite+aiosqlite", "sqlite")
sync_engine = create_engine(_sync_db_url)
SyncSession = sessionmaker(bind=sync_engine)


@celery_app.task(bind=True, name="process_document")
def process_document_task(self, document_id: int):
    """
    Full document processing pipeline:
    1. Extract text from the uploaded file
    2. Split text into chunks
    3. Generate embeddings
    4. Index in FAISS
    
    Args:
        document_id: ID of the document to process.
    """
    from backend.models.document import Document, DocumentStatus
    from backend.models.chunk import DocumentChunk
    from backend.services.document_processor import extract_text
    from backend.services.embedding_service import embed_texts
    from backend.services.vector_store import add_embeddings
    from backend.utils.text_utils import chunk_text
    
    session = SyncSession()
    
    try:
        # Get document
        doc = session.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error("document_not_found", document_id=document_id)
            return
        
        # Update status: processing
        doc.status = DocumentStatus.PROCESSING
        session.commit()
        self.update_state(state="PROCESSING", meta={"step": "extracting_text"})
        
        # Step 1: Extract text
        logger.info("extracting_text", document_id=document_id)
        result = extract_text(doc.file_path, doc.file_type)
        
        doc.text_content = result["text"]
        doc.page_count = result["page_count"]
        doc.word_count = result["word_count"]
        doc.language = result["language"]
        doc.metadata_json = result["metadata_json"]
        session.commit()
        
        # Step 2: Chunk text
        doc.status = DocumentStatus.CHUNKING
        session.commit()
        self.update_state(state="CHUNKING", meta={"step": "chunking_text"})
        
        logger.info("chunking_text", document_id=document_id)
        chunks = chunk_text(result["text"], chunk_size=1000, chunk_overlap=200)
        
        # Save chunks to DB
        db_chunks = []
        for i, chunk_data in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=i,
                content=chunk_data["content"],
                start_char=chunk_data["start_char"],
                end_char=chunk_data["end_char"],
                token_count=len(chunk_data["content"].split()),
            )
            session.add(chunk)
            db_chunks.append(chunk)
        
        session.flush()  # Get IDs assigned
        
        # Step 3: Generate embeddings
        doc.status = DocumentStatus.EMBEDDING
        session.commit()
        self.update_state(state="EMBEDDING", meta={"step": "generating_embeddings"})
        
        logger.info("generating_embeddings", document_id=document_id, chunks=len(db_chunks))
        chunk_texts = [c.content for c in db_chunks]
        embeddings = embed_texts(chunk_texts)
        
        # Step 4: Index in FAISS
        chunk_ids = [c.id for c in db_chunks]
        chunk_indices = [c.chunk_index for c in db_chunks]
        faiss_ids = add_embeddings(document_id, chunk_ids, chunk_indices, embeddings)
        
        # Update embedding IDs
        for chunk, fid in zip(db_chunks, faiss_ids):
            chunk.embedding_id = fid
        
        # Mark as ready
        doc.status = DocumentStatus.READY
        doc.updated_at = datetime.utcnow()
        session.commit()
        
        logger.info(
            "document_processed",
            document_id=document_id,
            chunks=len(db_chunks),
            status="ready",
        )
        
        return {"document_id": document_id, "status": "ready", "chunks": len(db_chunks)}
        
    except Exception as e:
        logger.error("document_processing_failed", document_id=document_id, error=str(e))
        try:
            doc = session.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(e)
                session.commit()
        except Exception:
            pass
        raise
    finally:
        session.close()


@celery_app.task(bind=True, name="generate_insights")
def generate_insights_task(self, document_id: int, doc_type: str = "general"):
    """
    Generate all AI insights for a document (summary, extraction, risk detection).
    
    Args:
        document_id: Document to analyze.
        doc_type: Document type for specialized extraction.
    """
    from backend.models.document import Document
    from backend.models.insight import DocumentInsight, InsightType
    from backend.services.rag_service import generate_summary, extract_key_info, detect_risks
    
    session = SyncSession()
    
    try:
        doc = session.query(Document).filter(Document.id == document_id).first()
        if not doc or not doc.text_content:
            logger.error("document_not_ready", document_id=document_id)
            return
        
        text = doc.text_content
        
        # Generate summary
        self.update_state(state="SUMMARIZING", meta={"step": "generating_summary"})
        summary = generate_summary(text, document_id)
        session.add(DocumentInsight(
            document_id=document_id,
            insight_type=InsightType.SUMMARY,
            content_json=json.dumps(summary),
        ))
        
        # Extract key info
        self.update_state(state="EXTRACTING", meta={"step": "extracting_info"})
        extraction = extract_key_info(text, document_id, doc_type)
        session.add(DocumentInsight(
            document_id=document_id,
            insight_type=InsightType.EXTRACTION,
            content_json=json.dumps(extraction),
        ))
        
        # Detect risks
        self.update_state(state="RISK_DETECTION", meta={"step": "detecting_risks"})
        risks = detect_risks(text, document_id)
        session.add(DocumentInsight(
            document_id=document_id,
            insight_type=InsightType.RISK,
            content_json=json.dumps(risks),
        ))
        
        session.commit()
        
        logger.info("insights_generated", document_id=document_id, doc_type=doc_type)
        return {"document_id": document_id, "insights_generated": 3}
        
    except Exception as e:
        logger.error("insight_generation_failed", document_id=document_id, error=str(e))
        raise
    finally:
        session.close()
