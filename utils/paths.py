"""Filesystem locations for OSINT Finder's persistent data.

On macOS, data lives under ~/Library/Application Support/OSINT Finder/.
On other platforms (used for development/testing) we fall back to a
reasonable equivalent so the app is still runnable off macOS, without ever
hardcoding a username or absolute path.
"""

from __future__ import annotations

from pathlib import Path

from utils.platform import is_macos, is_windows

APP_NAME = "OSINT Finder"


def app_support_dir() -> Path:
    home = Path.home()
    if is_macos():
        return home / "Library" / "Application Support" / APP_NAME
    if is_windows():
        import os

        base = os.environ.get("APPDATA", str(home))
        return Path(base) / APP_NAME
    # Linux / other (development fallback)
    return home / ".local" / "share" / APP_NAME.lower().replace(" ", "-")


def cache_dir() -> Path:
    return app_support_dir() / "cache"


def search_cache_dir() -> Path:
    return cache_dir() / "search"


def avatar_cache_dir() -> Path:
    return cache_dir() / "avatars"


def logs_dir() -> Path:
    return app_support_dir() / "logs"


def config_dir() -> Path:
    return app_support_dir() / "config"


def ensure_app_directories() -> None:
    for path in (search_cache_dir(), avatar_cache_dir(), logs_dir(), config_dir()):
        path.mkdir(parents=True, exist_ok=True)
