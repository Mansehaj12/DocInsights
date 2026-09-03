"""
FAISS-based vector store with IVF index for scalable similarity search.
Thread-safe with persistence and document-level filtering.
"""

import os
import json
from pathlib import Path
from threading import RLock
from typing import Optional

import numpy as np

from backend.config import get_settings
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)

# Thread-safe global state
_lock = RLock()
_faiss_index = None
_id_map: dict[int, dict] = {}
_next_id: int = 0

# IVF training threshold
_IVF_THRESHOLD = 256  # Use IndexIVFFlat when we have >= this many vectors


def _get_index_path() -> str:
    settings = get_settings()
    return settings.faiss_index_path


def _ensure_index_dir():
    index_path = _get_index_path()
    parent = os.path.dirname(index_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def get_or_create_index(dimension: int = 384):
    """
    Get existing FAISS index or create a new one.
    Uses IndexFlatIP for small datasets, upgrades to IndexIVFFlat for scale.
    """
    global _faiss_index, _id_map, _next_id

    with _lock:
        if _faiss_index is not None:
            return _faiss_index

        import faiss

        index_path = _get_index_path()

        # Try to load existing index
        if os.path.exists(index_path + ".index"):
            try:
                temp_index = faiss.read_index(index_path + ".index")
                
                # Check for dimension mismatch (e.g., switched from local to OpenAI models)
                if temp_index.d != dimension:
                    logger.warning(
                        "faiss_index_dimension_mismatch",
                        expected=dimension, 
                        actual=temp_index.d,
                        msg="Creating a fresh index"
                    )
                    # Fall through to create new index
                else:
                    _faiss_index = temp_index
                    if os.path.exists(index_path + ".map.json"):
                        with open(index_path + ".map.json", "r") as f:
                            saved = json.load(f)
                            _id_map = {int(k): v for k, v in saved.items()}
                            _next_id = max(_id_map.keys(), default=-1) + 1
                    logger.info("faiss_index_loaded", total_vectors=_faiss_index.ntotal)
                    return _faiss_index
            except Exception as e:
                logger.warning("faiss_index_load_failed", error=str(e))

        # Create new flat index (upgraded to IVF when enough vectors accumulate)
        _faiss_index = faiss.IndexFlatIP(dimension)
        _id_map = {}
        _next_id = 0

        logger.info("faiss_index_created", dimension=dimension, type="IndexFlatIP")
        return _faiss_index


def _maybe_upgrade_to_ivf():
    """Upgrade to IndexIVFFlat if enough vectors and currently using flat index."""
    global _faiss_index

    import faiss

    if _faiss_index is None or _faiss_index.ntotal < _IVF_THRESHOLD:
        return
    if not isinstance(_faiss_index, faiss.IndexFlatIP):
        return  # Already upgraded

    dim = _faiss_index.d
    n_vectors = _faiss_index.ntotal
    nlist = min(int(np.sqrt(n_vectors)), 64)  # Number of clusters

    logger.info("upgrading_to_ivf", n_vectors=n_vectors, nlist=nlist)

    # Reconstruct all vectors
    all_vectors = np.zeros((n_vectors, dim), dtype=np.float32)
    for i in range(n_vectors):
        all_vectors[i] = _faiss_index.reconstruct(i)

    # Build IVF index
    quantizer = faiss.IndexFlatIP(dim)
    new_index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT)
    new_index.train(all_vectors)
    new_index.add(all_vectors)
    new_index.nprobe = min(nlist, 10)  # Search 10 clusters for quality

    _faiss_index = new_index
    save_index()
    logger.info("ivf_upgrade_complete", n_vectors=n_vectors, nlist=nlist)


def add_embeddings(
    document_id: int,
    chunk_ids: list[int],
    chunk_indices: list[int],
    embeddings: np.ndarray,
) -> list[int]:
    """Add document chunk embeddings to the FAISS index (thread-safe)."""
    global _next_id

    with _lock:
        index = get_or_create_index(embeddings.shape[1])

        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)

        start_id = _next_id
        index.add(embeddings)

        faiss_ids = []
        for i, (chunk_id, chunk_idx) in enumerate(zip(chunk_ids, chunk_indices)):
            fid = start_id + i
            _id_map[fid] = {
                "document_id": document_id,
                "chunk_id": chunk_id,
                "chunk_index": chunk_idx,
            }
            faiss_ids.append(fid)

        _next_id = start_id + len(chunk_ids)
        save_index()

    # Try to upgrade index outside lock
    _maybe_upgrade_to_ivf()

    logger.info(
        "embeddings_added",
        document_id=document_id,
        count=len(chunk_ids),
        total_vectors=index.ntotal,
    )

    return faiss_ids


def search(
    query_embedding: np.ndarray,
    top_k: int = 5,
    document_id: Optional[int] = None,
) -> list[dict]:
    """Search for similar chunks using cosine similarity (thread-safe)."""
    with _lock:
        index = get_or_create_index()

        if index.ntotal == 0:
            return []

        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        if query_embedding.dtype != np.float32:
            query_embedding = query_embedding.astype(np.float32)

        search_k = top_k * 5 if document_id else top_k
        search_k = min(search_k, 50)  # Bounded over-fetch: never exceed 50
        search_k = min(search_k, index.ntotal)

        scores, indices = index.search(query_embedding, search_k)

    # Process results outside lock
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        chunk_info = _id_map.get(int(idx))
        if chunk_info is None:
            continue

        if document_id and chunk_info["document_id"] != document_id:
            continue

        results.append({
            "chunk_id": chunk_info["chunk_id"],
            "document_id": chunk_info["document_id"],
            "chunk_index": chunk_info["chunk_index"],
            "score": float(score),
        })

        if len(results) >= top_k:
            break

    return results


def delete_document_embeddings(document_id: int) -> int:
    """Remove all embeddings for a document (rebuilds index)."""
    global _faiss_index, _id_map, _next_id

    with _lock:
        ids_to_remove = [
            fid for fid, info in _id_map.items()
            if info["document_id"] == document_id
        ]

        if not ids_to_remove:
            return 0

        for fid in ids_to_remove:
            del _id_map[fid]

        if _id_map:
            import faiss

            old_index = _faiss_index
            dim = old_index.d
            new_index = faiss.IndexFlatIP(dim)

            remaining_ids = sorted(_id_map.keys())
            new_id_map = {}

            for new_fid, old_fid in enumerate(remaining_ids):
                vec = old_index.reconstruct(old_fid).reshape(1, -1)
                new_index.add(vec)
                new_id_map[new_fid] = _id_map[old_fid]

            _faiss_index = new_index
            _id_map = new_id_map
            _next_id = len(new_id_map)
        else:
            _faiss_index = None
            _next_id = 0

        save_index()

    logger.info("embeddings_deleted", document_id=document_id, count=len(ids_to_remove))
    return len(ids_to_remove)


def save_index():
    """Persist the FAISS index and ID map to disk."""
    if _faiss_index is None:
        return

    import faiss

    _ensure_index_dir()
    index_path = _get_index_path()

    faiss.write_index(_faiss_index, index_path + ".index")
    with open(index_path + ".map.json", "w") as f:
        json.dump(_id_map, f)

    logger.info("faiss_index_saved", path=index_path, vectors=_faiss_index.ntotal)


def get_index_stats() -> dict:
    """Get stats about the current FAISS index."""
    import faiss

    with _lock:
        index = get_or_create_index()
        index_type = type(index).__name__
        return {
            "total_vectors": index.ntotal,
            "dimension": index.d,
            "index_type": index_type,
            "documents_indexed": len(set(
                info["document_id"] for info in _id_map.values()
            )),
        }
