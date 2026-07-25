"""
app/services/rate_limit.py
Simple in-memory sliding-window rate limiter, per user_id + bucket name.
Good enough for a single-process deployment (matches the BackgroundTasks
"not a true distributed queue" honesty note in the roadmap) — if you scale
to multiple workers/machines, swap this for Redis-backed limiting.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException

_hits = defaultdict(list)
_lock = Lock()


def enforce(bucket: str, user_id: str, max_per_minute: int):
    """Raises HTTP 429 if this user has exceeded max_per_minute calls to
    `bucket` in the last 60 seconds. Call this at the top of any route that
    calls the paid OpenAI API or an external search API."""
    key = f"{bucket}:{user_id}"
    now = time.time()
    with _lock:
        recent = [t for t in _hits[key] if now - t < 60]
        if len(recent) >= max_per_minute:
            _hits[key] = recent
            raise HTTPException(
                status_code=429,
                detail=f"You're sending requests too quickly. Please wait a moment and try again.",
            )
        recent.append(now)
        _hits[key] = recent
