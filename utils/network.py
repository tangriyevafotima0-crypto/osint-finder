"""Centralized, bounded HTTP behavior for enrichment and avatar fetches.

This module deliberately does NOT provide any mechanism to bypass CAPTCHAs,
rate limits, authentication, or anti-bot protections. If a request is
blocked or fails, callers are expected to fall back to placeholders /
original discovery data rather than retry aggressively.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from utils.logger import get_logger

logger = get_logger("network")

USER_AGENT = "OSINT-Finder/1.0 (+public-profile-discovery; respectful-client)"

CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 8.0
TOTAL_TIMEOUT = 12.0

MAX_IMAGE_BYTES = 256 * 1024  # 256 KB
MAX_IMAGE_DIMENSION = 1024


@dataclass
class FetchResult:
    ok: bool
    status_code: Optional[int] = None
    text: Optional[str] = None
    content: Optional[bytes] = None
    content_type: Optional[str] = None
    error: Optional[str] = None


def _timeout() -> httpx.Timeout:
    return httpx.Timeout(connect=CONNECT_TIMEOUT, read=READ_TIMEOUT, write=READ_TIMEOUT, pool=TOTAL_TIMEOUT)


async def get_text(url: str, *, max_retries: int = 1) -> FetchResult:
    """Single reusable GET for enrichment. Max 1 retry, per spec."""
    attempts = max_retries + 1
    last_error = None

    async with httpx.AsyncClient(
        timeout=_timeout(), headers={"User-Agent": USER_AGENT}, follow_redirects=True
    ) as client:
        for attempt in range(attempts):
            try:
                resp = await client.get(url)
                return FetchResult(
                    ok=resp.status_code < 400,
                    status_code=resp.status_code,
                    text=resp.text,
                    content_type=resp.headers.get("content-type"),
                )
            except httpx.HTTPError as exc:
                last_error = str(exc)
                logger.debug(f"GET failed (attempt {attempt + 1}/{attempts}) for {url}: {exc}")

    return FetchResult(ok=False, error=last_error)


async def get_image(url: str, *, max_retries: int = 1) -> FetchResult:
    """Download an image with size limits enforced during streaming.

    Rejects non-image content types and anything exceeding MAX_IMAGE_BYTES.
    """
    attempts = max_retries + 1
    last_error = None

    async with httpx.AsyncClient(
        timeout=_timeout(), headers={"User-Agent": USER_AGENT}, follow_redirects=True
    ) as client:
        for attempt in range(attempts):
            try:
                async with client.stream("GET", url) as resp:
                    if resp.status_code >= 400:
                        last_error = f"HTTP {resp.status_code}"
                        continue

                    content_type = resp.headers.get("content-type", "")
                    if not content_type.startswith("image/"):
                        return FetchResult(ok=False, error=f"Not an image: {content_type}")

                    chunks = bytearray()
                    async for chunk in resp.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > MAX_IMAGE_BYTES:
                            return FetchResult(ok=False, error="Image exceeds size limit")

                    return FetchResult(
                        ok=True,
                        status_code=resp.status_code,
                        content=bytes(chunks),
                        content_type=content_type,
                    )
            except httpx.HTTPError as exc:
                last_error = str(exc)
                logger.debug(f"Image GET failed (attempt {attempt + 1}/{attempts}) for {url}: {exc}")

    return FetchResult(ok=False, error=last_error)


async def check_internet() -> bool:
    """Lightweight connectivity check used only during first-run setup."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.head("https://pypi.org", follow_redirects=True)
            return resp.status_code < 500
    except httpx.HTTPError:
        return False
