"""
AI Report Generation Service.
Generates comprehensive PDF reports using cached/new insights.

Features:
- Reuses existing insights from document_insights table (cache).
- Per-step timeout guard via _has_time() (90s total budget).
- Graceful degradation: if LLM fails, report still generates with available data.
- Uses fpdf2 for PDF generation (pure Python, no system deps).
"""

import json
import time
from datetime import datetime

from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.document import Document, DocumentStatus
from backend.models.insight import DocumentInsight, InsightType
from backend.services.rag_service import generate_summary, extract_key_info, detect_risks
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)

REPORT_GENERATION_TIMEOUT = 90  # seconds — total budget for entire report


class ReportGenerationError(Exception):
    """Raised for hard failures (doc not found, etc). Caught in API layer."""
    pass


async def generate_report(
    document_id: int,
    db: AsyncSession,
    report_type: str = "comprehensive",
) -> dict:
    """
    Generate a PDF report for a document.

    Strategy:
    1. Fetch document metadata
    2. Check for cached insights (reuse from document_insights table)
    3. Generate missing insights (with per-step timeout guard)
    4. Build PDF from all available data (even if some steps failed)

    Returns: {"pdf_bytes": bytes, "filename": str}
    Raises: ReportGenerationError on hard failure (doc not found, etc.)
    """
    start_time = time.time()
    logger.info("report_generation_start", document_id=document_id, report_type=report_type)

    # --- 1. Fetch document ---
    result = await db.execute(select(Document).filter(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise ReportGenerationError("Document not found")
    if doc.status != DocumentStatus.READY:
        raise ReportGenerationError(f"Document not ready. Status: {doc.status}")

    # --- 2. Check for cached insights ---
    result = await db.execute(
        select(DocumentInsight)
        .filter(DocumentInsight.document_id == document_id)
        .order_by(DocumentInsight.created_at.desc())
    )
    existing_insights = result.scalars().all()

    cached = {}
    for insight in existing_insights:
        if insight.insight_type.value not in cached:
            try:
                cached[insight.insight_type.value] = json.loads(insight.content_json)
            except json.JSONDecodeError:
                pass

    logger.info(
        "report_cache_status",
        cached_types=list(cached.keys()),
        document_id=document_id,
    )

    # --- 3. Generate missing insights (each with try/except + timeout check) ---
    summary_data = cached.get("summary")
    risk_data = cached.get("risk")
    extraction_data = cached.get("extraction")

    if not summary_data and _has_time(start_time):
        try:
            t0 = time.time()
            summary_data = generate_summary(doc.text_content, document_id)
            logger.info("report_summary_generated", latency_ms=round((time.time() - t0) * 1000))
        except Exception as e:
            logger.warning("report_summary_failed", error=str(e))
            summary_data = None

    if not risk_data and _has_time(start_time):
        try:
            t0 = time.time()
            risk_data = detect_risks(doc.text_content, document_id)
            logger.info("report_risks_generated", latency_ms=round((time.time() - t0) * 1000))
        except Exception as e:
            logger.warning("report_risks_failed", error=str(e))
            risk_data = None

    if not extraction_data and _has_time(start_time):
        try:
            t0 = time.time()
            extraction_data = extract_key_info(doc.text_content, document_id)
            logger.info("report_extraction_generated", latency_ms=round((time.time() - t0) * 1000))
        except Exception as e:
            logger.warning("report_extraction_failed", error=str(e))
            extraction_data = None

    # --- 4. Build PDF (always succeeds — uses whatever data is available) ---
    pdf_bytes = _build_pdf(doc, summary_data, risk_data, extraction_data)

    elapsed = round((time.time() - start_time) * 1000)
    logger.info(
        "report_generation_complete",
        document_id=document_id,
        elapsed_ms=elapsed,
        sections_generated=sum(1 for x in [summary_data, risk_data, extraction_data] if x),
    )

    safe_name = doc.original_filename.rsplit(".", 1)[0].replace(" ", "_")
    filename = f"DocInsights_Report_{safe_name}.pdf"
    return {"pdf_bytes": pdf_bytes, "filename": filename}


def _has_time(start_time: float) -> bool:
    """Check if we still have budget within the overall timeout."""
    return (time.time() - start_time) < REPORT_GENERATION_TIMEOUT


def _build_pdf(doc, summary, risks, extraction) -> bytes:
    """Build PDF using fpdf2. Pure function — no I/O, no LLM calls."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- Title ---
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 15, "DocInsights AI Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    # --- Document Metadata ---
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(
        0, 7,
        f"Document: {doc.original_filename}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.cell(
        0, 7,
        f"Type: {doc.file_type.upper()}  |  Pages: {doc.page_count or 'N/A'}  |  Words: {doc.word_count or 'N/A'}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.cell(
        0, 7,
        f"Language: {doc.language or 'N/A'}  |  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    # --- Horizontal rule ---
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    # --- Executive Summary ---
    if summary:
        _add_section(pdf, "Executive Summary", summary.get("executive_summary", ""))
        highlights = summary.get("bullet_highlights", [])
        if highlights:
            _add_section(pdf, "Key Highlights", "\n".join(f"  - {h}" for h in highlights))
        takeaways = summary.get("key_takeaways", [])
        if takeaways:
            _add_section(pdf, "Key Takeaways", "\n".join(f"  - {t}" for t in takeaways))

    # --- Risk Analysis ---
    if risks:
        risk_text = f"Overall Risk Level: {risks.get('overall_risk_score', 'N/A')}\n"
        risk_text += f"Total Risks Found: {risks.get('total_risks', len(risks.get('risk_items', [])))}\n"
        for item in risks.get("risk_items", []):
            risk_text += f"\n  [{item.get('severity', '?')}] {item.get('risk_type', '')}"
            risk_text += f"\n    {item.get('description', '')}"
            if item.get("recommendation"):
                risk_text += f"\n    Recommendation: {item['recommendation']}"
        _add_section(pdf, "Risk Analysis", risk_text)

    # --- Extracted Information ---
    if extraction:
        ext_lines = []
        for key, value in extraction.items():
            if isinstance(value, list):
                ext_lines.append(f"{key.replace('_', ' ').title()}:")
                for v in value:
                    ext_lines.append(f"  - {v if isinstance(v, str) else json.dumps(v)}")
            elif isinstance(value, dict):
                ext_lines.append(f"{key.replace('_', ' ').title()}:")
                for k2, v2 in value.items():
                    ext_lines.append(f"  {k2}: {v2}")
            else:
                ext_lines.append(f"{key.replace('_', ' ').title()}: {value}")
        _add_section(pdf, "Extracted Information", "\n".join(ext_lines))

    # --- Footer note if sections were missing ---
    generated_sections = sum(1 for x in [summary, risks, extraction] if x)
    if generated_sections < 3:
        pdf.ln(10)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(150, 150, 150)
        missing = []
        if not summary:
            missing.append("Summary")
        if not risks:
            missing.append("Risk Analysis")
        if not extraction:
            missing.append("Extraction")
        pdf.multi_cell(
            0, 5,
            f"Note: {', '.join(missing)} section(s) could not be generated. "
            "Run the corresponding analysis from the document page and regenerate this report.",
        )
        pdf.set_text_color(0, 0, 0)

    return pdf.output()


def _add_section(pdf, title, content):
    """Add a titled section to the PDF."""
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(30, 30, 120)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    
    # Sanitize content for Helvetica (which uses latin-1 in fpdf2 by default)
    content = content or "No data available."
    content = content.replace("\u2022", "-").replace("•", "-")
    content = content.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    content = content.replace("–", "-").replace("—", "-")
    # Encode/decode to wipe out any other unrenderable unicode characters
    content = content.encode("latin-1", "replace").decode("latin-1")
    
    # fpdf2 handles wrapping via multi_cell
    pdf.multi_cell(0, 6, content)
    pdf.ln(6)
