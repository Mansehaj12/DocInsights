"""
File validation and sanitization utilities.
Checks file types, sizes, and protects against malicious uploads.
"""

import os
import re
from pathlib import Path

from backend.config import get_settings
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)

# Magic bytes for file type verification
MAGIC_BYTES = {
    "pdf": b"%PDF",
    "docx": b"PK\x03\x04",  # ZIP-based format
    "txt": None,  # Text files have no specific magic bytes
}


class FileValidationError(Exception):
    """Raised when a file fails validation."""
    pass


def validate_file_extension(filename: str) -> str:
    """
    Validate and return the file extension.
    
    Args:
        filename: Original filename from upload.
        
    Returns:
        Lowercase file extension without dot.
        
    Raises:
        FileValidationError: If extension is not allowed.
    """
    settings = get_settings()
    ext = Path(filename).suffix.lower().lstrip(".")
    
    if not ext:
        raise FileValidationError("File has no extension")
    
    if ext not in settings.allowed_extensions_list:
        raise FileValidationError(
            f"File type '.{ext}' not allowed. Allowed: {settings.allowed_extensions_list}"
        )
    
    return ext


def validate_file_size(file_size: int) -> None:
    """
    Validate file size against configured limit.
    
    Args:
        file_size: Size in bytes.
        
    Raises:
        FileValidationError: If file exceeds size limit.
    """
    settings = get_settings()
    if file_size > settings.max_file_size_bytes:
        raise FileValidationError(
            f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds "
            f"limit ({settings.max_file_size_mb}MB)"
        )


def validate_magic_bytes(content: bytes, expected_type: str) -> None:
    """
    Verify file content matches expected type using magic bytes.
    
    Args:
        content: First bytes of the file.
        expected_type: Expected file type (pdf, docx, txt).
        
    Raises:
        FileValidationError: If magic bytes don't match.
    """
    expected_magic = MAGIC_BYTES.get(expected_type)
    
    if expected_magic is None:
        return  # No magic bytes to check (e.g., txt files)
    
    if not content.startswith(expected_magic):
        raise FileValidationError(
            f"File content does not match expected type '{expected_type}'"
        )


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and injection attacks.
    
    Args:
        filename: Original filename.
        
    Returns:
        Sanitized filename safe for storage.
    """
    # Remove path separators
    filename = os.path.basename(filename)
    
    # Remove potentially dangerous characters
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")
    
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200 - len(ext)] + ext
    
    # Fallback for empty filename
    if not filename:
        filename = "unnamed_file"
    
    return filename


def ensure_upload_dir() -> Path:
    """Create upload directory if it doesn't exist."""
    settings = get_settings()
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path
