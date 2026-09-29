"""Generic public-metadata enrichment for non-Instagram results.

This performs a best-effort, single-request fetch of the public profile
page and tries to pull an og:title / og:description / og:image out of the
HTML head. It never logs in, never bypasses CAPTCHAs/rate limits, and
never retries more than once. If anything fails, the original result is
returned unmodified.
"""

from __future__ import annotations

import re
from typing import Optional

from core.models import SearchResult
from utils.logger import get_logger
from utils.network import get_text

logger = get_logger("profile_enrichment")

_META_PATTERN = re.compile(
    r'<meta[^>]+property=["\']og:(title|description|image)["\'][^>]+content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)


def _extract_og_tags(html: str) -> dict:
    tags = {}
    for match in _META_PATTERN.finditer(html):
        key, value = match.group(1), match.group(2)
        if key not in tags:
            tags[key] = value
    return tags


async def enrich_profile(result: SearchResult) -> SearchResult:
    """Best-effort public metadata enrichment. Never raises, never crashes search."""
    try:
        fetch = await get_text(result.profile_url, max_retries=1)
        if not fetch.ok or not fetch.text:
            return result

        tags = _extract_og_tags(fetch.text)
        if tags.get("title"):
            result.title = tags["title"][:200]
        if tags.get("description"):
            result.description = tags["description"][:400]
        if tags.get("image") and not result.avatar_url:
            result.avatar_url = tags["image"]

    except Exception as exc:  # noqa: BLE001 - enrichment must never crash the app
        logger.debug(f"Profile enrichment failed for {result.profile_url}: {exc}")

    return result
