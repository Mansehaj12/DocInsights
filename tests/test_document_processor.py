"""
Unit tests for document processing, text utilities, and vector store.
"""

import os
import tempfile

import pytest


# ============================================
# Text Utility Tests
# ============================================

class TestTextUtils:
    """Tests for text cleaning and chunking."""
    
    def test_clean_text_normalizes_whitespace(self):
        from backend.utils.text_utils import clean_text
        text = "Hello\r\nWorld\r\n\r\n\r\n\r\nTest"
        result = clean_text(text)
        assert "\r" not in result
        assert "\n\n\n" not in result
    
    def test_clean_text_removes_null_bytes(self):
        from backend.utils.text_utils import clean_text
        text = "Hello\x00World"
        result = clean_text(text)
        assert "\x00" not in result
        assert "HelloWorld" in result
    
    def test_clean_text_empty_string(self):
        from backend.utils.text_utils import clean_text
        assert clean_text("") == ""
        assert clean_text(None) == ""
    
    def test_chunk_text_basic(self):
        from backend.utils.text_utils import chunk_text
        text = "A" * 2500
        chunks = chunk_text(text, chunk_size=1000, chunk_overlap=200)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert "content" in chunk
            assert "start_char" in chunk
            assert "end_char" in chunk
    
    def test_chunk_text_small_text(self):
        from backend.utils.text_utils import chunk_text
        text = "Small text"
        chunks = chunk_text(text, chunk_size=1000, chunk_overlap=200)
        assert len(chunks) == 1
        assert chunks[0]["content"] == "Small text"
    
    def test_chunk_text_empty(self):
        from backend.utils.text_utils import chunk_text
        assert chunk_text("") == []
    
    def test_count_words(self):
        from backend.utils.text_utils import count_words
        assert count_words("Hello World Test") == 3
        assert count_words("") == 0
    
    def test_detect_language_english(self):
        from backend.utils.text_utils import detect_language
        result = detect_language("This is a test sentence in English language for detection purposes.")
        assert result == "en"


# ============================================
# File Validator Tests
# ============================================

class TestFileValidator:
    """Tests for file validation and sanitization."""
    
    def test_validate_extension_valid(self):
        from backend.utils.file_validator import validate_file_extension
        assert validate_file_extension("test.pdf") == "pdf"
        assert validate_file_extension("test.docx") == "docx"
        assert validate_file_extension("test.txt") == "txt"
    
    def test_validate_extension_invalid(self):
        from backend.utils.file_validator import validate_file_extension, FileValidationError
        with pytest.raises(FileValidationError):
            validate_file_extension("test.exe")
    
    def test_validate_extension_none(self):
        from backend.utils.file_validator import validate_file_extension, FileValidationError
        with pytest.raises(FileValidationError):
            validate_file_extension("noextension")
    
    def test_validate_file_size_ok(self):
        from backend.utils.file_validator import validate_file_size
        validate_file_size(1024)  # 1KB should be fine
    
    def test_validate_file_size_too_large(self):
        from backend.utils.file_validator import validate_file_size, FileValidationError
        with pytest.raises(FileValidationError):
            validate_file_size(100 * 1024 * 1024)  # 100MB
    
    def test_sanitize_filename(self):
        from backend.utils.file_validator import sanitize_filename
        assert sanitize_filename("../../../etc/passwd") == "passwd"
        assert sanitize_filename("test<script>.pdf") == "testscript.pdf"
        assert sanitize_filename("normal_file.pdf") == "normal_file.pdf"
    
    def test_sanitize_empty_filename(self):
        from backend.utils.file_validator import sanitize_filename
        result = sanitize_filename("")
        assert result == "unnamed_file"


# ============================================
# Document Processor Tests
# ============================================

class TestDocumentProcessor:
    """Tests for document text extraction."""
    
    def test_extract_text_txt(self):
        from backend.services.document_processor import extract_text
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello World! This is a test document with multiple words.")
            f.flush()
            
            result = extract_text(f.name, "txt")
            
            assert "Hello World" in result["text"]
            assert result["word_count"] > 0
            assert result["language"] == "en"
        
        os.unlink(f.name)
    
    def test_extract_text_invalid_type(self):
        from backend.services.document_processor import extract_text
        
        with pytest.raises(ValueError, match="Unsupported"):
            extract_text("test.xyz", "xyz")


# ============================================
# Config Tests
# ============================================

class TestConfig:
    """Tests for application configuration."""
    
    def test_settings_defaults(self):
        from backend.config import Settings
        settings = Settings()
        assert settings.app_name == "Smart Document Insights"
        assert settings.max_file_size_mb == 50
    
    def test_max_file_size_bytes(self):
        from backend.config import Settings
        settings = Settings()
        assert settings.max_file_size_bytes == 50 * 1024 * 1024
    
    def test_allowed_extensions_list(self):
        from backend.config import Settings
        settings = Settings()
        assert "pdf" in settings.allowed_extensions_list
        assert "docx" in settings.allowed_extensions_list
        assert "txt" in settings.allowed_extensions_list


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
