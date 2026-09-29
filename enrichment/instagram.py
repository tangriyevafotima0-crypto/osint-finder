"""Instagram-priority enrichment.

Uses the same publicly-accessible-page approach as generic profile
enrichment (og:title/description/image), since that's what's legitimately
available without logging in. Kept as a separate module because Instagram
gets enrichment priority per spec, and this is the natural seam for a
more tailored public-data extraction later (Phase 2) without touching
the generic profile enricher.
"""

from __future__ import annotations

from core.models import SearchResult
from enrichment.profile import enrich_profile
from utils.logger import get_logger

logger = get_logger("instagram_enrichment")


async def enrich_instagram(result: SearchResult) -> SearchResult:
    """Best-effort public Instagram metadata enrichment.

    Never attempts login, CAPTCHA bypass, or private-account access.
    Falls back to the original result on any failure.
    """
    try:
        return await enrich_profile(result)
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Instagram enrichment failed for {result.profile_url}: {exc}")
        return result
