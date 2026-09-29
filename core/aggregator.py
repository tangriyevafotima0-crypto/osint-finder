"""Combine and deduplicate results coming from one or more engines.

Dedup key = normalized platform name + normalized profile URL.
When the same (platform, url) is found by multiple engines, we merge into
a single SearchResult and record all contributing engines.
"""

from __future__ import annotations

from typing import Dict, List

from core.models import SearchResult
from core.normalize import normalize_platform_name, normalize_profile_url


def _dedup_key(result: SearchResult) -> str:
    if result.dedup_key:
        return result.dedup_key
    platform = normalize_platform_name(result.platform).lower()
    url = normalize_profile_url(result.profile_url)
    return f"{platform}::{url}"


def deduplicate(results: List[SearchResult]) -> List[SearchResult]:
    """Merge duplicate (platform, url) results, preserving first-seen order."""
    merged: Dict[str, SearchResult] = {}

    for result in results:
        key = _dedup_key(result)
        result.dedup_key = key

        if key not in merged:
            merged[key] = result
            continue

        existing = merged[key]
        for engine in result.source_engines:
            if engine not in existing.source_engines:
                existing.source_engines.append(engine)

        # Prefer whichever record already has richer metadata; fill gaps
        # from the incoming duplicate without discarding existing data.
        existing.title = existing.title or result.title
        existing.description = existing.description or result.description
        existing.avatar_url = existing.avatar_url or result.avatar_url

    return list(merged.values())
