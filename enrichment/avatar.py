"""Lazy avatar download + disk cache + thumbnailing.

Avatars are only fetched when a result has been selected for enrichment,
never during initial discovery. Duplicate URLs reuse the cached file.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from utils.logger import get_logger
from utils.network import MAX_IMAGE_DIMENSION, get_image
from utils.paths import avatar_cache_dir

logger = get_logger("avatar")

THUMBNAIL_SIZES = [(64, 64), (96, 96)]


def _cache_filename(avatar_url: str) -> str:
    digest = hashlib.sha256(avatar_url.encode("utf-8")).hexdigest()[:24]
    return f"avatar_{digest}.jpg"


def cached_path(avatar_url: str) -> Path:
    return avatar_cache_dir() / _cache_filename(avatar_url)


async def fetch_avatar(avatar_url: str) -> Optional[str]:
    """Download (or reuse cached) avatar, returning a local file path.

    Returns None if the avatar cannot legitimately be retrieved — callers
    must fall back to a placeholder rather than treat this as fatal.
    """
    if not avatar_url:
        return None

    target = cached_path(avatar_url)
    if target.exists():
        return str(target)

    result = await get_image(avatar_url, max_retries=1)
    if not result.ok or not result.content:
        logger.debug(f"Avatar fetch failed for {avatar_url}: {result.error}")
        return None

    processed = _process_image(result.content)
    if processed is None:
        logger.debug(f"Avatar processing failed for {avatar_url}")
        return None

    try:
        avatar_cache_dir().mkdir(parents=True, exist_ok=True)
        target.write_bytes(processed)
    except OSError as exc:
        logger.error(f"Failed to write avatar cache file {target}: {exc}")
        return None

    return str(target)


def _process_image(raw_bytes: bytes) -> Optional[bytes]:
    """Validate, downscale if needed, and re-encode as JPEG.

    Returns None on any failure (caller shows a placeholder instead).
    """
    try:
        from io import BytesIO

        from PIL import Image

        img = Image.open(BytesIO(raw_bytes))
        img.verify()  # validate it's really an image, not junk/malformed data

        # Re-open after verify() (which leaves the file unusable for further ops)
        img = Image.open(BytesIO(raw_bytes))
        img = img.convert("RGB")

        if img.width > MAX_IMAGE_DIMENSION or img.height > MAX_IMAGE_DIMENSION:
            img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))

        out = BytesIO()
        img.save(out, format="JPEG", quality=85)
        return out.getvalue()
    except Exception as exc:  # noqa: BLE001 - any bad/unexpected image data
        logger.debug(f"Image validation/processing error: {exc}")
        return None


def make_thumbnail(source_path: str, size: tuple) -> Optional[bytes]:
    """Produce a small thumbnail (e.g. for a 64x64 or 96x96 GUI avatar)."""
    try:
        from io import BytesIO

        from PIL import Image

        img = Image.open(source_path)
        img = img.convert("RGB")
        img.thumbnail(size)
        out = BytesIO()
        img.save(out, format="JPEG", quality=85)
        return out.getvalue()
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Thumbnail generation failed for {source_path}: {exc}")
        return None
