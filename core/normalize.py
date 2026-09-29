"""Input normalization.

Phase 1 scope: only handle obvious formats (leading @, full profile URLs
for a handful of common platforms, surrounding whitespace). We deliberately
do NOT generate username variants/mutations here.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

_PROFILE_URL_PATTERNS = [
    re.compile(r"^(?:https?://)?(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)/?"),
    re.compile(r"^(?:https?://)?(?:www\.)?(?:twitter|x)\.com/([A-Za-z0-9_]+)/?"),
    re.compile(r"^(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9-]+)/?"),
    re.compile(r"^(?:https?://)?(?:www\.)?reddit\.com/u(?:ser)?/([A-Za-z0-9_-]+)/?"),
    re.compile(r"^(?:https?://)?(?:www\.)?tiktok\.com/@([A-Za-z0-9_.]+)/?"),
    re.compile(r"^(?:https?://)?(?:www\.)?youtube\.com/@([A-Za-z0-9_.-]+)/?"),
]


def normalize_username(raw: str) -> str:
    """Normalize obvious input formats into a bare username.

    Examples:
        "@john_smith"                       -> "john_smith"
        "https://instagram.com/john_smith"  -> "john_smith"
        "  john_smith  "                    -> "john_smith"
    """
    if raw is None:
        return ""

    value = raw.strip()
    if not value:
        return ""

    for pattern in _PROFILE_URL_PATTERNS:
        match = pattern.match(value)
        if match:
            return match.group(1)

    if value.startswith("@"):
        value = value[1:]

    return value.strip()


def is_valid_username(username: str) -> bool:
    if not username:
        return False
    if len(username) > 100:
        return False
    # Reject whitespace/control characters; allow the practical range of
    # characters seen across platform username schemes.
    return bool(re.match(r"^[A-Za-z0-9_.\-]+$", username))


def normalize_profile_url(url: str) -> str:
    """Normalize a profile URL enough to support duplicate detection.

    - lowercase scheme/host
    - drop 'www.'
    - drop trailing slash
    - drop query string / fragment
    """
    if not url:
        return ""

    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "").rstrip("/")

    return f"{host}{path}".lower()


def normalize_platform_name(name: str) -> str:
    if not name:
        return ""
    cleaned = name.strip()
    # A couple of common aliasing cases so "X" and "Twitter" results from
    # different engines/data can still be recognized consistently for
    # ranking purposes (dedup itself uses URL, not this).
    lowered = cleaned.lower()
    if lowered == "x.com":
        return "X"
    return cleaned
