"""Central logging setup.

Never logs passwords, tokens, cookies, private messages, or authentication
data — none of that data ever exists in this app's models to begin with.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_CONFIGURED = False


def _configure_root():
    global _CONFIGURED
    if _CONFIGURED:
        return

    from utils.paths import logs_dir

    log_dir = logs_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "osint_finder.log"

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    root = logging.getLogger("osint_finder")
    root.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # If we can't write logs to disk, still keep console logging alive.
        pass

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(f"osint_finder.{name}")
