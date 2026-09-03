"""
RAG v2 — Multi-Document Retrieval-Augmented Generation.
Isolated from rag_service.py to avoid breaking existing single-doc pipeline.

Includes:
- Bounded FAISS over-fetch (MAX_OVERFETCH cap)
- Per-document chunk caps + deduplication
- Token-aware context building with round-robin balancing
- Timeout-safe LLM calls via safe_llm_call()
- Comprehensive latency logging
"""

import time
from collections import defaultdict

from backend.services.llm_client import safe_llm_call
from backend.services.prompts import MULTI_DOC_QA_PROMPT
from backend.services.embedding_service import embed_query
from backend.services.vector_store import search as faiss_search
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)

# --- Retrieval constants ---
MAX_CONTEXT_TOKENS = 6000
MAX_CHUNKS_PER_DOC = 3
MAX_TOTAL_CHUNKS = 10
TOKEN_ESTIMATE_RATIO = 4
MAX_OVERFETCH = 50  # Hard cap on FAISS over-fetch


def ask_multi_document(
    question: str,
    document_ids: list[int],
    chunks_by_doc: dict[int, list[dict]],
    doc_names: dict[int, str],
    top_k: int = 5,
) -> dict:
    """
    Answer a question across multiple documents using RAG.

    Pipeline:
    1. Embed question
    2. FAISS global search with bounded over-fetch: min(top_k*3, MAX_OVERFETCH)
    3. Filter by allowed document_ids
    4. Deduplicate by chunk_id
    5. Cap per-document chunks (MAX_CHUNKS_PER_DOC)
    6. Re-rank by score (descending)
    7. Build token-aware context with round-robin doc balancing
    8. LLM call with MULTI_DOC_QA_PROMPT via safe_llm_call() (20s timeout)

    Returns: {answer, sources, highlights, document_groups}
    On LLM timeout/failure: returns fallback answer, still includes sources/highlights.
    """
    logger.info("multi_doc_query", document_ids=document_ids, question=question[:80])
    t_start = time.time()

    # --- 1. Embed ---
    t_embed = time.time()
    query_embedding = embed_query(question)
    embed_ms = round((time.time() - t_embed) * 1000)
    logger.info("multi_doc_embed_time", latency_ms=embed_ms)

    # --- 2. FAISS global search (bounded over-fetch) ---
    overfetch_k = min(top_k * 3, MAX_OVERFETCH)

    t_retrieve = time.time()
    search_results = faiss_search(
        query_embedding=query_embedding,
        top_k=overfetch_k,
        document_id=None,  # global — no pre-filter
    )
    retrieve_ms = round((time.time() - t_retrieve) * 1000)
    logger.info(
        "multi_doc_retrieval_time",
        latency_ms=retrieve_ms,
        raw_results=len(search_results),
        overfetch_k=overfetch_k,
    )

    # --- 3. Filter by allowed document_ids ---
    allowed = set(document_ids)
    filtered = [r for r in search_results if r["document_id"] in allowed]

    # --- 4. Deduplicate by chunk_id ---
    seen_chunks = set()
    unique = []
    for r in filtered:
        if r["chunk_id"] not in seen_chunks:
            seen_chunks.add(r["chunk_id"])
            unique.append(r)

    # --- 5. Per-document cap ---
    doc_counts = defaultdict(int)
    capped = []
    for r in unique:
        if doc_counts[r["document_id"]] < MAX_CHUNKS_PER_DOC:
            capped.append(r)
            doc_counts[r["document_id"]] += 1

    # --- 6. Re-rank by score ---
    capped.sort(key=lambda x: x["score"], reverse=True)

    if not capped:
        return {
            "answer": "I couldn't find relevant information across the selected documents.",
            "sources": [],
            "highlights": [],
            "document_groups": [],
        }

    # Build chunk lookup (all docs)
    all_chunks = {}
    for doc_id, chunks in chunks_by_doc.items():
        for c in chunks:
            all_chunks[c["id"]] = {**c, "document_id": doc_id}

    # --- Build sources + highlights ---
    grouped = defaultdict(list)
    sources = []
    highlights = []

    for result in capped:
        chunk = all_chunks.get(result["chunk_id"])
        if not chunk:
            continue

        grouped[result["document_id"]].append(chunk)
        sources.append({
            "chunk_id": result["chunk_id"],
            "document_id": result["document_id"],
            "document_name": doc_names.get(result["document_id"], "Unknown"),
            "chunk_index": result["chunk_index"],
            "content": chunk["content"][:200],
            "relevance_score": result["score"],
        })

        try:
            highlights.append({
                "document_id": result["document_id"],
                "page_number": chunk.get("start_page"),
                "chunk_index": result["chunk_index"],
                "text": chunk["content"],
                "start_char": chunk.get("start_char"),
                "end_char": chunk.get("end_char"),
                "relevance_score": result["score"],
            })
        except Exception:
            pass  # highlight is best-effort, never blocks response

    # --- 7. Token-aware context ---
    context = _build_multi_doc_context(grouped, doc_names)

    # --- 8. LLM call (timeout-safe) ---
    doc_list = ", ".join(doc_names.get(did, f"Doc {did}") for did in document_ids)
    prompt = MULTI_DOC_QA_PROMPT.format(
        documents=doc_list,
        context=context,
        question=question,
    )

    t_llm = time.time()
    answer = safe_llm_call(
        prompt,
        timeout=20,
        use_cache=False,
        fallback="I was unable to analyze the documents at the moment. Please try again.",
    )
    llm_ms = round((time.time() - t_llm) * 1000)
    logger.info("multi_doc_llm_time", latency_ms=llm_ms)

    # --- Build document_groups ---
    document_groups = []
    for doc_id in document_ids:
        doc_sources = [s for s in sources if s["document_id"] == doc_id]
        if doc_sources:
            document_groups.append({
                "document_id": doc_id,
                "document_name": doc_names.get(doc_id, "Unknown"),
                "sources": doc_sources,
            })

    total_ms = round((time.time() - t_start) * 1000)
    logger.info(
        "multi_doc_answer_generated",
        document_count=len(document_ids),
        sources_count=len(sources),
        embed_ms=embed_ms,
        retrieve_ms=retrieve_ms,
        llm_ms=llm_ms,
        total_latency_ms=total_ms,
    )

    return {
        "answer": answer,
        "sources": sources,
        "highlights": highlights,
        "document_groups": document_groups,
    }


def _build_multi_doc_context(grouped_chunks, doc_names):
    """
    Token-aware, round-robin context builder.

    Iterates across documents in round-robin order, taking one chunk
    at a time from each, until MAX_TOTAL_CHUNKS or MAX_CONTEXT_TOKENS
    is reached. The last chunk is truncated (not discarded) if it
    would exceed the token budget.
    """
    context_parts = []
    estimated_tokens = 0
    chunks_used = 0

    doc_ids = list(grouped_chunks.keys())
    doc_iters = {did: iter(chunks) for did, chunks in grouped_chunks.items()}

    while chunks_used < MAX_TOTAL_CHUNKS:
        added_any = False
        for did in doc_ids:
            if chunks_used >= MAX_TOTAL_CHUNKS or estimated_tokens >= MAX_CONTEXT_TOKENS:
                break
            try:
                chunk = next(doc_iters[did])
            except StopIteration:
                continue

            chunk_text = chunk["content"]
            chunk_tokens = len(chunk_text) // TOKEN_ESTIMATE_RATIO

            if estimated_tokens + chunk_tokens > MAX_CONTEXT_TOKENS:
                remaining_chars = (MAX_CONTEXT_TOKENS - estimated_tokens) * TOKEN_ESTIMATE_RATIO
                if remaining_chars < 100:
                    break  # not enough room for meaningful content
                chunk_text = chunk_text[:remaining_chars] + "..."
                chunk_tokens = remaining_chars // TOKEN_ESTIMATE_RATIO

            doc_name = doc_names.get(did, f"Document {did}")
            context_parts.append(
                f"[{doc_name} \u2014 Chunk {chunk['chunk_index'] + 1}]: {chunk_text}"
            )
            estimated_tokens += chunk_tokens
            chunks_used += 1
            added_any = True

        if not added_any or estimated_tokens >= MAX_CONTEXT_TOKENS:
            break

    return "\n\n".join(context_parts)
