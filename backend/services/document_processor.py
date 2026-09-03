"""
Document processing service — extracts text from PDF, DOCX, and TXT files.
Supports OCR for scanned documents via pytesseract.
"""

import json
import os
from pathlib import Path

from backend.utils.logging_config import get_logger
from backend.utils.text_utils import clean_text, count_words, detect_language

logger = get_logger(__name__)


def extract_text_pdf(file_path: str) -> dict:
    """
    Extract text from a PDF file using PyMuPDF.
    Falls back to OCR (pytesseract) for scanned pages.
    
    Args:
        file_path: Path to the PDF file.
        
    Returns:
        Dict with 'text', 'page_count', 'metadata'.
    """
    import fitz  # PyMuPDF
    
    doc = fitz.open(file_path)
    pages_text = []
    ocr_used = False
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        
        # If very little text found, try OCR
        if len(text.strip()) < 50:
            try:
                import pytesseract
                from PIL import Image
                import io
                
                # Render page as image
                mat = fitz.Matrix(1.5, 1.5)  # 1.5x zoom (reduced from 2x for memory safety)
                pix = page.get_pixmap(matrix=mat)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                
                ocr_text = pytesseract.image_to_string(img)
                if len(ocr_text.strip()) > len(text.strip()):
                    text = ocr_text
                    ocr_used = True
            except ImportError:
                logger.warning("pytesseract_not_available", page=page_num)
            except Exception as e:
                logger.warning("ocr_failed", page=page_num, error=str(e))
        
        pages_text.append(text)
    
    # Extract metadata
    metadata = doc.metadata or {}
    page_count = len(doc)
    doc.close()
    
    full_text = clean_text("\n\n".join(pages_text))
    
    logger.info(
        "pdf_extracted",
        file=os.path.basename(file_path),
        pages=page_count,
        chars=len(full_text),
        ocr_used=ocr_used,
    )
    
    return {
        "text": full_text,
        "page_count": page_count,
        "metadata": {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
            "ocr_used": ocr_used,
        },
    }


def extract_text_docx(file_path: str) -> dict:
    """
    Extract text from a DOCX file using python-docx.
    
    Args:
        file_path: Path to the DOCX file.
        
    Returns:
        Dict with 'text', 'page_count', 'metadata'.
    """
    from docx import Document
    
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full_text = clean_text("\n\n".join(paragraphs))
    
    # Extract core properties
    core = doc.core_properties
    metadata = {
        "title": core.title or "",
        "author": core.author or "",
        "subject": core.subject or "",
        "created": str(core.created) if core.created else "",
        "modified": str(core.modified) if core.modified else "",
    }
    
    # Estimate pages (DOCX doesn't have fixed pages)
    estimated_pages = max(1, len(full_text) // 3000)
    
    logger.info(
        "docx_extracted",
        file=os.path.basename(file_path),
        paragraphs=len(paragraphs),
        chars=len(full_text),
    )
    
    return {
        "text": full_text,
        "page_count": estimated_pages,
        "metadata": metadata,
    }


def extract_text_txt(file_path: str) -> dict:
    """
    Extract text from a plain text file with encoding detection.
    
    Args:
        file_path: Path to the TXT file.
        
    Returns:
        Dict with 'text', 'page_count', 'metadata'.
    """
    import chardet
    
    # Detect encoding
    with open(file_path, "rb") as f:
        raw_data = f.read()
    
    detected = chardet.detect(raw_data)
    encoding = detected.get("encoding", "utf-8") or "utf-8"
    
    try:
        text = raw_data.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        text = raw_data.decode("utf-8", errors="replace")
    
    full_text = clean_text(text)
    estimated_pages = max(1, len(full_text) // 3000)
    
    logger.info(
        "txt_extracted",
        file=os.path.basename(file_path),
        encoding=encoding,
        chars=len(full_text),
    )
    
    return {
        "text": full_text,
        "page_count": estimated_pages,
        "metadata": {"encoding": encoding, "confidence": detected.get("confidence", 0)},
    }


def extract_text(file_path: str, file_type: str) -> dict:
    """
    Extract text from a document based on its type.
    
    Args:
        file_path: Path to the document.
        file_type: File type (pdf, docx, txt).
        
    Returns:
        Dict with 'text', 'page_count', 'word_count', 'language', 'metadata'.
    """
    extractors = {
        "pdf": extract_text_pdf,
        "docx": extract_text_docx,
        "txt": extract_text_txt,
    }
    
    extractor = extractors.get(file_type)
    if not extractor:
        raise ValueError(f"Unsupported file type: {file_type}")
    
    result = extractor(file_path)
    
    # Enrich with common fields
    result["word_count"] = count_words(result["text"])
    result["language"] = detect_language(result["text"])
    result["metadata_json"] = json.dumps(result["metadata"])
    
    return result
