"""
Smart Document Insights — FastAPI Application Entry Point.
Production-ready AI SaaS platform for document analysis and insights.
"""

import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.database import init_db
from backend.services.llm_context import clear_request_llm_override, set_request_llm_override
from backend.utils.logging_config import get_logger, setup_logging

# Built React app (produced by `npm run build` in frontend/). Served as the UI.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

# Initialize logging
settings = get_settings()
setup_logging(debug=settings.debug)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("application_starting", app_name=settings.app_name, env=settings.app_env)

    # Create data directories
    os.makedirs("data/uploads", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # Initialize database
    await init_db()
    logger.info("database_initialized")

    # Check LLM configuration
    if settings.is_llm_configured:
        logger.info("llm_configured", model=settings.openai_model)
    else:
        logger.warning("llm_not_configured", msg="Running in demo mode. Set OPENAI_API_KEY for full features.")

    yield

    logger.info("application_shutting_down")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI-powered document analysis with semantic search, RAG chat, risk detection, and insights.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Bring-your-own-key middleware.
# Reads an OpenAI-compatible key (and optional model/base) from request headers,
# applies it for the duration of this request only, and clears it afterwards.
# The key is held in a contextvar — never written to disk, the DB, or the logs.
@app.middleware("http")
async def apply_byo_key(request: Request, call_next):
    token = set_request_llm_override(
        api_key=request.headers.get("X-LLM-API-Key"),
        model=request.headers.get("X-LLM-Model"),
        base_url=request.headers.get("X-LLM-Base-URL"),
    )
    try:
        return await call_next(request)
    finally:
        clear_request_llm_override(token)


# Request logging + timing middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log requests with timing and request ID."""
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    response = await call_next(request)

    duration_ms = round((time.time() - start) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration_ms}ms"

    logger.info(
        "request",
        method=request.method,
        path=str(request.url.path),
        status=response.status_code,
        duration_ms=duration_ms,
        request_id=request_id,
    )

    return response


# Structured error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return structured JSON errors."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=str(request.url.path),
        method=request.method,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again.",
        },
    )


# ============================================
# Register API routes (versioned + compat)
# ============================================
from backend.api.documents import router as documents_router
from backend.api.insights import router as insights_router
from backend.api.search import router as search_router
from backend.api.chat import router as chat_router
from backend.api.compare import router as compare_router
from backend.api.dashboard import router as dashboard_router
from backend.api.report import router as report_router
from backend.api.chat_v2 import router as chat_v2_router

# Register under both /api/ and /api/v1/ for compatibility
for router in [documents_router, insights_router, search_router, chat_router, compare_router, dashboard_router]:
    app.include_router(router)

# Register new feature routers (v2)
app.include_router(report_router)
app.include_router(chat_v2_router)


# ============================================
# System endpoints
# ============================================

@app.get("/api/health", tags=["System"])
@app.get("/api/v1/health", tags=["System"], include_in_schema=False)
async def health_check():
    """Health check with version and LLM status."""
    from backend.services.llm_client import get_cache_stats
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "2.0.0",
        "llm_configured": settings.is_llm_configured,
        "llm_model": settings.openai_model if settings.is_llm_configured else None,
        "cache": get_cache_stats(),
    }


# ============================================
# Serve the React single-page app
# ============================================
# The built frontend lives in frontend/dist. We mount its hashed asset bundles
# at /assets and serve index.html for all other (non-API) routes so client-side
# routing (/upload, /search, ...) works on hard refresh. Registered LAST so the
# /api/* routers and /docs take precedence.

if FRONTEND_DIST.is_dir():
    _assets_dir = FRONTEND_DIST / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    _index_file = FRONTEND_DIST / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve a matching static file, else fall back to index.html (SPA)."""
        # Never let the SPA shadow the API surface.
        if full_path.startswith(("api/", "docs", "redoc", "openapi.json")):
            return JSONResponse(status_code=404, content={"error": "not_found"})

        candidate = (FRONTEND_DIST / full_path).resolve()
        # Guard against path traversal, then serve real files (favicon, etc.).
        if candidate.is_file() and str(candidate).startswith(str(FRONTEND_DIST.resolve())):
            return FileResponse(candidate)

        return FileResponse(_index_file)
else:
    @app.get("/", tags=["System"])
    async def root():
        """Fallback API info when the frontend has not been built."""
        return {
            "app": settings.app_name,
            "version": "2.0.0",
            "docs": "/docs",
            "health": "/api/health",
            "note": "Frontend not built. Run `npm run build` in frontend/.",
        }


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", "8000"))
    logger.info("starting_uvicorn_server", port=port, host="0.0.0.0")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=settings.app_env == "development")
