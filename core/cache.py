"""Search result cache.

- One JSON file per (username, mode) under cache/search/.
- Fast search TTL: 30 minutes. Deep search TTL: 60 minutes.
- Corrupted/unreadable cache files are deleted and treated as a miss,
  never crash the app.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Optional

from core.models import SearchMode, SearchResult
from utils.logger import get_logger
from utils.paths import search_cache_dir

logger = get_logger("cache")

FAST_TTL_SECONDS = 30 * 60
DEEP_TTL_SECONDS = 60 * 60


def _ttl_for_mode(mode: SearchMode) -> int:
    return DEEP_TTL_SECONDS if mode == SearchMode.DEEP else FAST_TTL_SECONDS


def _cache_path(username: str, mode: SearchMode) -> Path:
    safe_username = "".join(c for c in username.lower() if c.isalnum() or c in "_-.") or "unknown"
    return search_cache_dir() / f"{safe_username}_{mode.value}.json"


def load(username: str, mode: SearchMode) -> Optional[List[SearchResult]]:
    """Return cached results if present and fresh, else None.

    Any corruption is treated as a cache miss; the bad file is removed.
    """
    path = _cache_path(username, mode)
    if not path.exists():
        return None

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error(f"Corrupted cache file {path}: {exc}. Removing.")
        _safe_remove(path)
        return None

    try:
        saved_at = data["saved_at"]
        results_data = data["results"]
    except (KeyError, TypeError) as exc:
        logger.error(f"Incompatible cache file {path}: {exc}. Removing.")
        _safe_remove(path)
        return None

    age = time.time() - saved_at
    if age > _ttl_for_mode(mode):
        logger.info(f"Cache expired for {username} ({mode.value}), age={age:.0f}s")
        return None

    try:
        return [SearchResult.from_json(r) for r in results_data]
    except (KeyError, ValueError) as exc:
        logger.error(f"Failed to parse cached results for {path}: {exc}. Removing.")
        _safe_remove(path)
        return None


def save(username: str, mode: SearchMode, results: List[SearchResult]) -> None:
    path = _cache_path(username, mode)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "saved_at": time.time(),
            "username": username,
            "mode": mode.value,
            "results": [r.to_json() for r in results],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.error(f"Failed to write cache file {path}: {exc}")


def _safe_remove(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
