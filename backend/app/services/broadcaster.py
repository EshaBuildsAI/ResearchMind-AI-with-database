"""
app/services/broadcaster.py
Simple in-memory pub-sub so agent_service can push step updates to any
WebSocket connected to that run's channel, in real time as each step
completes — instead of the frontend waiting for the whole run to finish.

Agent work runs in a background THREAD (FastAPI/Starlette BackgroundTasks
use a thread pool for sync functions), not the main asyncio thread. Calling
asyncio.get_event_loop() from that worker thread doesn't reliably return
the server's actual running loop — it silently fails, which meant every
publish() call from a streaming agent run was a no-op: the DB write still
succeeded (so Agent History always showed the full result), but nothing
ever reached the WebSocket, so the live panel sat stuck on "Starting agent
pipeline...". Fix: capture the real loop once at startup and always target
that specific loop with call_soon_threadsafe.

In-process only (same caveat as rate_limit.py): fine for one server
process; swap for Redis pub-sub if you scale to multiple workers/machines.
"""

import asyncio
import json
import logging
from collections import defaultdict

logger = logging.getLogger("researchmind")

_subscribers = defaultdict(list)  # run_id -> [asyncio.Queue, ...]
_main_loop = None  # set once via set_main_loop() at app startup


def set_main_loop(loop: asyncio.AbstractEventLoop):
    global _main_loop
    _main_loop = loop


def subscribe(run_id: str) -> asyncio.Queue:
    queue = asyncio.Queue()
    _subscribers[run_id].append(queue)
    return queue


def unsubscribe(run_id: str, queue: asyncio.Queue):
    if queue in _subscribers[run_id]:
        _subscribers[run_id].remove(queue)
    if not _subscribers[run_id]:
        _subscribers.pop(run_id, None)


def publish(run_id: str, event: dict):
    """Called from synchronous agent_service code — which may be running in
    a background worker thread, not the main event loop thread. Safe to
    call even if no loop is registered yet or no one is subscribed."""
    queues = _subscribers.get(run_id, [])
    if not queues:
        return
    if _main_loop is None:
        logger.warning("broadcaster.publish called before set_main_loop() — event dropped.")
        return
    payload = json.dumps(event)
    for q in queues:
        try:
            _main_loop.call_soon_threadsafe(q.put_nowait, payload)
        except Exception as e:
            logger.warning(f"broadcaster.publish failed for run {run_id}: {e}")