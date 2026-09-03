"""
Text processing utilities for cleaning, language detection, and encoding.
"""

import re
import unicodedata

from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


def clean_text(text: str) -> str:
    """
    Clean and normalize extracted text.
    
    Args:
        text: Raw extracted text.
        
    Returns:
        Cleaned text with normalized whitespace and removed artifacts.
    """
    if not text:
        return ""
    
    # Normalize Unicode
    text = unicodedata.normalize("NFKC", text)
    
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Remove excessive whitespace (more than 2 consecutive newlines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove lines that are just whitespace
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def detect_language(text: str) -> str:
    """
    Detect the language of text.
    
    Args:
        text: Text to analyze.
        
    Returns:
        ISO language code (e.g., 'en', 'es').
    """
    try:
        from langdetect import detect
        if len(text) < 20:
            return "en"  # Default for very short text
        # Use first 5000 chars for speed
        return detect(text[:5000])
    except Exception:
        return "en"


def count_words(text: str) -> int:
    """Count words in text."""
    if not text:
        return 0
    return len(text.split())


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[dict]:
    """
    Split text into overlapping chunks for embedding.
    
    Uses a recursive approach: tries to split on paragraphs first,
    then sentences, then words.
    
    Args:
        text: Full text to chunk.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Number of overlapping characters between chunks.
        
    Returns:
        List of dicts with 'content', 'start_char', 'end_char' keys.
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        
        # Try to break at a paragraph boundary
        if end < text_len:
            # Look for paragraph break near the end
            para_break = text.rfind("\n\n", start + chunk_size // 2, end)
            if para_break != -1:
                end = para_break + 2
            else:
                # Try sentence break
                sentence_break = max(
                    text.rfind(". ", start + chunk_size // 2, end),
                    text.rfind("! ", start + chunk_size // 2, end),
                    text.rfind("? ", start + chunk_size // 2, end),
                )
                if sentence_break != -1:
                    end = sentence_break + 2
                else:
                    # Fallback: break at word boundary
                    word_break = text.rfind(" ", start + chunk_size // 2, end)
                    if word_break != -1:
                        end = word_break + 1
        
        chunk_content = text[start:end].strip()
        if chunk_content:
            chunks.append({
                "content": chunk_content,
                "start_char": start,
                "end_char": end,
            })
        
        # Move start forward, accounting for overlap
        start = end - chunk_overlap if end < text_len else text_len
    
    logger.info("text_chunked", num_chunks=len(chunks), text_length=text_len)
    return chunks
