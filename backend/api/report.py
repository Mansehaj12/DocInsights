"""
Report generation API routes.
POST /api/report/generate — generates a PDF report for a document.
"""

import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_db
from backend.models.schemas import ReportRequest
from backend.services.report_service import generate_report, ReportGenerationError
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/report", tags=["Report"])


@router.post("/generate")
async def generate_document_report(
    request: ReportRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a comprehensive PDF report for a document.
    Returns PDF as a streaming download.
    On failure: returns structured JSON error — never crashes.
    """
    settings = get_settings()
    if not settings.enable_report_generation:
        raise HTTPException(status_code=403, detail="Report generation is currently disabled")

    try:
        result = await generate_report(request.document_id, db, request.report_type)
        return StreamingResponse(
            io.BytesIO(result["pdf_bytes"]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{result["filename"]}"'
            },
        )
    except ReportGenerationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("report_generation_error", error=str(e), document_id=request.document_id)
        raise HTTPException(
            status_code=500,
            detail="Report generation encountered an error. Please try again.",
        )
