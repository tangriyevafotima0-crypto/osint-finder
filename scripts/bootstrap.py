#!/usr/bin/env python3
"""Diagnostics for OSINT Finder's environment.

Run:
    python3 scripts/bootstrap.py --diagnose

Does NOT perform an OSINT search. Only checks that the environment is
ready (OS, architecture, Python, dependencies, cache directories, internet).
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MIN_PYTHON = (3, 10)

CHECKS = [
    ("PySide6", "PySide6"),
    ("Maigret", "maigret"),
    ("httpx", "httpx"),
    ("Pillow", "PIL"),
]


def _ok(label: str):
    print(f"[OK] {label}")


def _fail(label: str, reason: str = ""):
    suffix = f" - {reason}" if reason else ""
    print(f"[FAIL] {label}{suffix}")


def check_os():
    from utils.platform import architecture, os_name

    name = os_name()
    if name == "Darwin":
        _ok("macOS")
    else:
        print(f"[INFO] Running on {name} (primary target is macOS)")
    _ok(architecture())


def check_python():
    version = sys.version_info
    if version >= MIN_PYTHON:
        _ok(f"Python {version.major}.{version.minor}.{version.micro}")
    else:
        _fail(
            f"Python {version.major}.{version.minor}.{version.micro}",
            f"requires >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
        )


def check_venv():
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if in_venv:
        _ok("Virtual environment")
    else:
        print("[INFO] Not running inside a virtual environment")


def check_dependencies():
    all_ok = True
    for label, module_name in CHECKS:
        try:
            importlib.import_module(module_name)
            _ok(label)
        except ImportError as exc:
            _fail(label, str(exc))
            all_ok = False
    return all_ok


def check_cache_dirs():
    from utils.paths import ensure_app_directories, app_support_dir

    try:
        ensure_app_directories()
        _ok(f"Cache directories ({app_support_dir()})")
    except OSError as exc:
        _fail("Cache directories", str(exc))


async def _check_internet_async() -> bool:
    from utils.network import check_internet

    return await check_internet()


def check_internet_connectivity():
    try:
        available = asyncio.run(_check_internet_async())
    except Exception as exc:  # noqa: BLE001
        _fail("Internet availability", str(exc))
        return
    if available:
        _ok("Internet availability")
    else:
        print("[INFO] No internet connection detected")


def main():
    parser = argparse.ArgumentParser(description="OSINT Finder diagnostics")
    parser.add_argument("--diagnose", action="store_true", help="Run environment diagnostics")
    args = parser.parse_args()

    if not args.diagnose:
        parser.print_help()
        return 0

    check_os()
    check_python()
    check_venv()
    deps_ok = check_dependencies()
    check_cache_dirs()
    check_internet_connectivity()

    if deps_ok:
        _ok("Environment ready")
        return 0
    else:
        _fail("Environment ready", "one or more dependencies missing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
