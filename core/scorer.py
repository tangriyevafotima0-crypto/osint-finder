"""Confidence scoring — a relevance ranking, NOT identity verification.

Score components (max 100):
    Profile found:                +40
    Exact username match:         +30
    High-priority platform:       +10
    Found by multiple engines:    +10
    Public metadata present:      +5
    Public avatar present:        +5
"""

from __future__ import annotations

from typing import List

from core.models import ResultStatus, SearchResult, confidence_label
from core.priority import TIER_HIGH, platform_tier

SCORE_FOUND = 40
SCORE_EXACT_USERNAME = 30
SCORE_HIGH_PRIORITY_PLATFORM = 10
SCORE_MULTI_ENGINE = 10
SCORE_METADATA = 5
SCORE_AVATAR = 5

MAX_SCORE = 100


def score_result(result: SearchResult, queried_username: str) -> int:
    score = 0

    if result.status == ResultStatus.FOUND:
        score += SCORE_FOUND

    if result.username.strip().lower() == queried_username.strip().lower():
        score += SCORE_EXACT_USERNAME

    if platform_tier(result.platform) == TIER_HIGH:
        score += SCORE_HIGH_PRIORITY_PLATFORM

    if len(result.source_engines) > 1:
        score += SCORE_MULTI_ENGINE

    if result.title or result.description:
        score += SCORE_METADATA

    if result.avatar_url or result.avatar_path:
        score += SCORE_AVATAR

    return min(score, MAX_SCORE)


def apply_scores(results: List[SearchResult], queried_username: str) -> List[SearchResult]:
    for result in results:
        result.confidence = score_result(result, queried_username)
        result.confidence_label = confidence_label(result.confidence)
    return results


def rank_results(results: List[SearchResult]) -> List[SearchResult]:
    """Sort by confidence (desc), platform tier as a tiebreaker."""
    tier_order = {TIER_HIGH: 0, "MEDIUM": 1, "LOW": 2}
    return sorted(
        results,
        key=lambda r: (-r.confidence, tier_order.get(platform_tier(r.platform), 2), r.platform.lower()),
    )
