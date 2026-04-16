"""Resource completion cache — 30-second TTL JSON cache for shell completion."""

from __future__ import annotations

import json
import time
from pathlib import Path

CACHE_TTL = 30  # seconds
_CACHE_DIR = Path.home() / ".orca" / "cache"


def _path(profile: str | None, resource: str) -> Path:
    return _CACHE_DIR / f"{profile or 'default'}_{resource}.json"


def load(profile: str | None, resource: str) -> list[dict] | None:
    """Return cached items if still fresh, else None."""
    try:
        p = _path(profile, resource)
        if not p.exists():
            return None
        data = json.loads(p.read_text())
        if time.time() - data.get("ts", 0) < CACHE_TTL:
            return data.get("items")
    except Exception:
        pass
    return None


def save(profile: str | None, resource: str, items: list[dict]) -> None:
    """Persist items to cache file."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _path(profile, resource).write_text(
            json.dumps({"ts": time.time(), "items": items})
        )
    except Exception:
        pass


def invalidate(profile: str | None, resource: str) -> None:
    """Delete a cache entry (call after create/delete operations)."""
    try:
        _path(profile, resource).unlink(missing_ok=True)
    except Exception:
        pass
