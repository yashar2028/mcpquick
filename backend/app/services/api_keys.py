"""Ephemeral API key storage for session-only run execution.

Keys are held in-process only and removed once consumed by the worker.
They are never persisted in the database.
"""

from __future__ import annotations

import asyncio
import time


_KEY_TTL_SECONDS = 3600
_key_store: dict[str, tuple[str, float]] = {}
_key_lock = asyncio.Lock()


def _prune_expired(now: float) -> None:
    expired_run_ids = [
        run_id
        for run_id, (_, inserted_at) in _key_store.items()
        if now - inserted_at > _KEY_TTL_SECONDS
    ]
    for run_id in expired_run_ids:
        _key_store.pop(run_id, None)


async def stash_run_api_key(run_id: str, api_key: str) -> None:
    """Store a run API key in memory until consumed by the worker."""
    now = time.time()
    async with _key_lock:
        _prune_expired(now)
        _key_store[run_id] = (api_key, now)


async def pop_run_api_key(run_id: str) -> str | None:
    """Return and remove the run API key from memory."""
    now = time.time()
    async with _key_lock:
        _prune_expired(now)
        value = _key_store.pop(run_id, None)

    if value is None:
        return None
    return value[0]
