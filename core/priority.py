"""Configurable platform priority tiers.

Kept as simple, editable data rather than logic scattered across the
codebase. Matching is case-insensitive against the platform/site name
returned by a search engine.
"""

from __future__ import annotations

from typing import Dict, List

HIGH_PRIORITY_PLATFORMS: List[str] = [
    "instagram",
    "github",
    "reddit",
    "twitter",
    "x",
    "youtube",
    "tiktok",
]

MEDIUM_PRIORITY_PLATFORMS: List[str] = [
    "linkedin",
    "facebook",
    "pinterest",
]

# Anything not found above falls into LOW.

TIER_HIGH = "HIGH"
TIER_MEDIUM = "MEDIUM"
TIER_LOW = "LOW"

_LOOKUP: Dict[str, str] = {}
for _name in HIGH_PRIORITY_PLATFORMS:
    _LOOKUP[_name.lower()] = TIER_HIGH
for _name in MEDIUM_PRIORITY_PLATFORMS:
    _LOOKUP[_name.lower()] = TIER_MEDIUM


def platform_tier(platform_name: str) -> str:
    """Return HIGH / MEDIUM / LOW for a given platform name."""
    return _LOOKUP.get(platform_name.strip().lower(), TIER_LOW)


def is_instagram(platform_name: str) -> bool:
    return platform_name.strip().lower() == "instagram"
