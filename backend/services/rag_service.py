"""
RAG (Retrieval-Augmented Generation) service.
Thin orchestrator that composes llm_client, prompts, and response_parser.

Pipeline: embed query → retrieve chunks → inject context → LLM response.
"""

from backend.services.llm_client import get_llm_response, get_llm_streaming, safe_llm_call
from backend.services.prompts import (
    QA_PROMPT,
    SUMMARY_PROMPT,
    RISK_DETECTION_PROMPT,
    COMPARISON_PROMPT,
    get_extraction_prompt,
)
from backend.services.response_parser import (
    parse_json_response,
    validate_summary_response,
    validate_risk_response,
    validate_comparison_response,
)
from backend.services.embedding_service import embed_query
from backend.services.vector_store import search as faiss_search
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


# ============================================
# RAG Question-Answering
# ============================================

def ask_question(
    question: str,
    document_id: int,
    chunks_data: list[dict],
    top_k: int = 5,
) -> dict:
    """
    Answer a question using RAG pipeline.
    
    Pipeline:
    1. Embed the question
    2. Search FAISS for relevant chunks
    3. Build context from retrieved chunks
    4. Call LLM with context + question
    
    Args:
        question: User's question.
        document_id: Target document ID.
        chunks_data: List of chunk dicts with 'id', 'content', 'chunk_index'.
        top_k: Number of chunks to retrieve.
    
    Returns:
        Dict with 'answer' and 'sources'.
    """
    logger.info("rag_query", document_id=document_id, question=question[:80])

    # Step 1: Embed the question
    query_embedding = embed_query(question)

    # Step 2: Search for relevant chunks
    search_results = faiss_search(
        query_embedding=query_embedding,
        top_k=top_k,
        document_id=document_id,
    )

    if not search_results:
        return {
            "answer": "I couldn't find relevant information in the document to answer your question.",
            "sources": [],
        }

    # Step 3: Build context from found chunks
    context_parts = []
    sources = []
    chunk_lookup = {c["id"]: c for c in chunks_data}

    for result in search_results:
        chunk = chunk_lookup.get(result["chunk_id"])
        if chunk:
            context_parts.append(f"[Chunk {result['chunk_index'] + 1}]: {chunk['content']}")
            sources.append({
                "chunk_id": result["chunk_id"],
                "chunk_index": result["chunk_index"],
                "content": chunk["content"][:200],
                "relevance_score": result["score"],
            })

    context = "\n\n".join(context_parts)

    # Step 4: Call LLM
    prompt = QA_PROMPT.format(context=context, question=question)
    answer = safe_llm_call(
        prompt,
        timeout=15,
        use_cache=False,
        fallback="I was unable to generate an answer at the moment. Please try again.",
    )

    # Step 5: Build highlights safely
    highlights = []
    try:
        for result in search_results:
            chunk = chunk_lookup.get(result["chunk_id"])
            if chunk:
                highlights.append({
                    "document_id": document_id,
                    "page_number": chunk.get("start_page"),
                    "chunk_index": result["chunk_index"],
                    "text": chunk["content"],
                    "start_char": chunk.get("start_char"),
                    "end_char": chunk.get("end_char"),
                    "relevance_score": result["score"],
                })
    except Exception as e:
        logger.warning("highlight_extraction_failed", error=str(e))
        highlights = []

    logger.info("rag_answer_generated", document_id=document_id, sources=len(sources))

    return {"answer": answer, "sources": sources, "highlights": highlights}


# ============================================
# Document Summarization
# ============================================

def generate_summary(text: str, document_id: int) -> dict:
    """Generate a comprehensive document summary."""
    logger.info("generating_summary", document_id=document_id, text_length=len(text))

    # Truncate long documents intelligently
    text = _smart_truncate(text, max_chars=12000)

    prompt = SUMMARY_PROMPT.format(text=text)
    response = get_llm_response(prompt)

    result = parse_json_response(response, default={
        "executive_summary": response,
        "section_summaries": [],
        "bullet_highlights": [],
        "key_takeaways": [],
    })

    return validate_summary_response(result)


# ============================================
# Key Information Extraction
# ============================================

def extract_key_info(text: str, document_id: int, doc_type: str = "general") -> dict:
    """Extract structured key information based on document type."""
    logger.info("extracting_info", document_id=document_id, doc_type=doc_type)

    text = _smart_truncate(text, max_chars=10000)
    prompt_template = get_extraction_prompt(doc_type)
    prompt = prompt_template.format(text=text)
    response = get_llm_response(prompt)

    return parse_json_response(response)


# ============================================
# Risk Detection
# ============================================

def detect_risks(text: str, document_id: int) -> dict:
    """Detect risks, compliance issues, and concerning language."""
    logger.info("detecting_risks", document_id=document_id, text_length=len(text))

    text = _smart_truncate(text, max_chars=10000)
    prompt = RISK_DETECTION_PROMPT.format(text=text)
    response = get_llm_response(prompt)

    result = parse_json_response(response, default={
        "overall_risk_score": "Medium",
        "risk_items": [],
    })

    return validate_risk_response(result)


# ============================================
# Document Comparison
# ============================================

def compare_documents(documents: list[dict]) -> dict:
    """Compare multiple documents for similarities and differences."""
    logger.info("comparing_documents", count=len(documents))

    documents_text = "\n\n---\n\n".join(
        f"DOCUMENT: {doc['filename']}\n{_smart_truncate(doc['text'], max_chars=5000)}"
        for doc in documents
    )

    prompt = COMPARISON_PROMPT.format(documents_text=documents_text)
    response = get_llm_response(prompt)

    result = parse_json_response(response, default={
        "summary": response,
        "similarities": [],
        "differences": [],
    })

    return validate_comparison_response(result)


# ============================================
# Helpers
# ============================================

def _smart_truncate(text: str, max_chars: int = 12000) -> str:
    """Truncate long text by taking beginning, middle, and end sections."""
    if len(text) <= max_chars:
        return text

    third = max_chars // 3
    return (
        text[:third]
        + "\n\n[...middle section...]\n\n"
        + text[len(text) // 2 - third // 2 : len(text) // 2 + third // 2]
        + "\n\n[...end section...]\n\n"
        + text[-third:]
    )
