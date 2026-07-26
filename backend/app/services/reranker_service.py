"""
app/services/reranker_service.py
Improves confidence scoring for citations: raw vector-similarity distance
(what vectorstore.py returns) is a rough first pass. A cross-encoder
re-ranker scores (question, passage) pairs directly and is significantly
more accurate — and it's free and runs locally (no API call), same spirit
as the free embedding model.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (~90MB, one-time download,
same HuggingFace-hub mechanism as the embedding model).
"""

import logging

logger = logging.getLogger("researchmind")

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _model


def rerank(question: str, candidates: list) -> list:
    """candidates: list of dicts with at least a 'text' key (as returned by
    vectorstore.query_with_metadata). Returns the same list, re-sorted by a
    calibrated 0-100 confidence score, replacing the rough similarity score."""
    if not candidates:
        return candidates
    try:
        model = _get_model()
        pairs = [(question, c["text"]) for c in candidates]
        raw_scores = model.predict(pairs)

        # Cross-encoder scores are unbounded logits — squash to 0-100 with a
        # sigmoid so the frontend's confidence chip stays meaningful.
        import math

        for candidate, score in zip(candidates, raw_scores):
            squashed = 1 / (1 + math.exp(-float(score)))
            candidate["confidence"] = round(squashed * 100, 1)

        candidates.sort(key=lambda c: c["confidence"], reverse=True)
        return candidates
    except Exception as e:
        # Re-ranking is an enhancement, not a hard dependency — if the model
        # can't load (e.g. no internet for the one-time download), fall back
        # to whatever confidence scores vectorstore already computed.
        logger.warning(f"Re-ranking unavailable, falling back to vector-similarity confidence: {e}")
        return candidates
