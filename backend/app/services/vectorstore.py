"""
app/services/vectorstore.py
Vector storage and semantic retrieval using ChromaDB, with free local
embeddings (all-MiniLM-L6-v2 via ChromaDB's default embedding function —
no OpenAI/paid embedding calls).

Per-user isolation is storage-level, not just an API convention: every
chunk is stored with BOTH doc_id and user_id in its metadata, and every
query/delete filters on user_id. A user can never retrieve or delete
another user's chunks even if they guess a doc_id.
"""

import os

os.environ["ANONYMIZED_TELEMETRY"] = "False"  # silence chromadb/posthog noise

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.utils.text import chunk_text, ensure_dir

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        ensure_dir(settings.CHROMA_DB_PATH)
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_DB_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(name=settings.CHROMA_COLLECTION_NAME)
    return _collection


def add_document(user_id: str, doc_id: str, filename: str, text: str, pages: list = None) -> int:
    """Chunk + embed a document's text, scoped to user_id. Returns chunk count."""
    collection = _get_collection()

    try:
        collection.delete(where={"$and": [{"doc_id": doc_id}, {"user_id": user_id}]})
    except Exception:
        pass  # nothing to delete yet — expected on first upload

    all_chunks, all_metadatas, all_ids = [], [], []

    if pages:
        counter = 0
        for page_num, page_text in pages:
            for chunk in chunk_text(page_text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP):
                all_chunks.append(chunk)
                all_metadatas.append({
                    "doc_id": doc_id, "user_id": user_id, "filename": filename,
                    "chunk_index": counter, "page": page_num,
                })
                all_ids.append(f"{user_id}_{doc_id}_chunk_{counter}")
                counter += 1
    else:
        for i, chunk in enumerate(chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)):
            all_chunks.append(chunk)
            all_metadatas.append({
                "doc_id": doc_id, "user_id": user_id, "filename": filename,
                "chunk_index": i, "page": 0,
            })
            all_ids.append(f"{user_id}_{doc_id}_chunk_{i}")

    if not all_chunks:
        return 0

    collection.add(documents=all_chunks, ids=all_ids, metadatas=all_metadatas)
    return len(all_chunks)


def _build_where(user_id: str, doc_id) -> dict:
    """doc_id can be None (search all of the user's docs), a single doc_id
    string, or a list of doc_ids (multi-document context)."""
    if not doc_id:
        return {"user_id": user_id}
    if isinstance(doc_id, (list, tuple, set)):
        doc_ids = list(doc_id)
        if len(doc_ids) == 1:
            return {"$and": [{"doc_id": doc_ids[0]}, {"user_id": user_id}]}
        return {"$and": [{"doc_id": {"$in": doc_ids}}, {"user_id": user_id}]}
    return {"$and": [{"doc_id": doc_id}, {"user_id": user_id}]}


def query(user_id: str, query_text: str, doc_id=None, n_results: int = None) -> list:
    """Retrieve relevant chunk texts, always scoped to user_id. doc_id may be
    a single id, a list of ids (multi-document context), or None (all docs)."""
    collection = _get_collection()
    n_results = n_results or settings.TOP_K_RESULTS

    where = _build_where(user_id, doc_id)
    results = collection.query(query_texts=[query_text], n_results=n_results, where=where)

    if not results["documents"]:
        return []
    return results["documents"][0]


def query_with_metadata(user_id: str, query_text: str, doc_id=None, n_results: int = None) -> list:
    """Like query(), but returns page number + filename + an approximate
    confidence score (derived from vector distance — a similarity signal,
    not a calibrated probability, unless reranker_service.rerank() is
    applied afterward). Used by the Citation Agent. doc_id may be a single
    id, a list of ids (multi-document context), or None (all docs)."""
    collection = _get_collection()
    n_results = n_results or settings.TOP_K_RESULTS

    where = _build_where(user_id, doc_id)
    results = collection.query(
        query_texts=[query_text], n_results=n_results, where=where,
        include=["documents", "metadatas", "distances"],
    )

    if not results["documents"] or not results["documents"][0]:
        return []

    chunks, metadatas, distances = results["documents"][0], results["metadatas"][0], results["distances"][0]
    output = []
    for text, meta, distance in zip(chunks, metadatas, distances):
        confidence = max(0.0, min(1.0, 1 - distance)) * 100
        output.append({
            "text": text, "page": meta.get("page") or None,
            "confidence": round(confidence, 1),
            "doc_id": meta.get("doc_id"), "filename": meta.get("filename"),
        })
    return output


def get_full_document_text(user_id: str, doc_id: str) -> str:
    collection = _get_collection()
    results = collection.get(where={"$and": [{"doc_id": doc_id}, {"user_id": user_id}]})
    if not results["documents"]:
        return ""
    paired = sorted(zip(results["metadatas"], results["documents"]), key=lambda p: p[0]["chunk_index"])
    return " ".join(chunk for _, chunk in paired)


def get_full_documents_text(user_id: str, doc_ids: list) -> str:
    """Multi-document context: concatenates full text of several documents,
    each labeled by filename so the LLM can attribute claims correctly."""
    parts = []
    collection = _get_collection()
    for doc_id in doc_ids:
        results = collection.get(where={"$and": [{"doc_id": doc_id}, {"user_id": user_id}]})
        if not results["documents"]:
            continue
        paired = sorted(zip(results["metadatas"], results["documents"]), key=lambda p: p[0]["chunk_index"])
        filename = paired[0][0].get("filename", doc_id) if paired else doc_id
        text = " ".join(chunk for _, chunk in paired)
        parts.append(f"[Document: {filename}]\n{text}")
    return "\n\n".join(parts)


def delete_document(user_id: str, doc_id: str):
    collection = _get_collection()
    collection.delete(where={"$and": [{"doc_id": doc_id}, {"user_id": user_id}]})


def delete_all_for_user(user_id: str):
    """Used by reset-workspace — clears every chunk belonging to this user."""
    collection = _get_collection()
    try:
        collection.delete(where={"user_id": user_id})
    except Exception:
        pass
