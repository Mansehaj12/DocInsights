"""
API integration tests using FastAPI TestClient.
"""

import os
import tempfile

import pytest
from httpx import AsyncClient, ASGITransport

from backend.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_check():
    """Test the health check endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.anyio
async def test_root():
    """Test root endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "docs" in data


@pytest.mark.anyio
async def test_list_documents_empty():
    """Test listing documents when none exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0


@pytest.mark.anyio
async def test_get_nonexistent_document():
    """Test getting a document that doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/documents/99999")
        assert response.status_code == 404


@pytest.mark.anyio
async def test_upload_invalid_file_type():
    """Test uploading an unsupported file type."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.exe", b"fake content", "application/octet-stream")},
        )
        assert response.status_code == 400


@pytest.mark.anyio
async def test_dashboard_stats():
    """Test dashboard stats endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data


@pytest.mark.anyio
async def test_search_empty_index():
    """Test search with empty vector index."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/search",
            json={"query": "test query", "top_k": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
