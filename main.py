#!/usr/bin/env python3
"""OSINT Finder — entry point."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is importable regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.logger import get_logger
from utils.paths import ensure_app_directories

logger = get_logger("main")


def main() -> int:
    ensure_app_directories()

    from PySide6.QtWidgets import QApplication

    from gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("OSINT Finder")

    window = MainWindow()
    window.show()

    logger.info("OSINT Finder started")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
