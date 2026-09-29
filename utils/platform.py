"""OS / architecture detection helpers."""

from __future__ import annotations

import platform


def is_macos() -> bool:
    return platform.system() == "Darwin"


def is_windows() -> bool:
    return platform.system() == "Windows"


def is_linux() -> bool:
    return platform.system() == "Linux"


def architecture() -> str:
    """Return 'arm64', 'x86_64', or whatever platform.machine() reports."""
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    return machine


def os_name() -> str:
    return platform.system()


def python_version() -> str:
    return platform.python_version()
