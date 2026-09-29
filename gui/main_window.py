"""OSINT Finder main window."""

from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.models import SearchMode, SearchResponse, SearchState
from core.search_manager import SearchManager
from gui.result_card import ResultCard
from gui.search_bar import SearchBar
from gui.workers import start_search
from utils.logger import get_logger

logger = get_logger("gui")

STATE_MESSAGES = {
    SearchState.IDLE: "Ready to search",
    SearchState.SEARCHING: "Searching public profiles...",
    SearchState.ENRICHING: "Enriching profiles...",
    SearchState.NO_RESULTS: "No public profiles found",
    SearchState.ERROR: "Search failed",
    SearchState.CANCELLED: "Search cancelled",
}

STYLESHEET = """
QMainWindow { background-color: #1e1e24; }
QLabel#appTitle { font-size: 22px; font-weight: 600; color: #f2f2f5; }
QLabel#appSubtitle { font-size: 13px; color: #9a9aa5; }
QLabel#fieldLabel { font-size: 12px; color: #9a9aa5; font-weight: 600; }
QLabel#statusLabel { font-size: 13px; color: #b5b5c0; padding: 4px 0; }
QLineEdit {
    background-color: #2a2a33; color: #f2f2f5; border: 1px solid #3a3a45;
    border-radius: 8px; padding: 10px 12px; font-size: 14px;
}
QPushButton#primaryButton {
    background-color: #5b6cff; color: white; border: none;
    border-radius: 8px; padding: 10px 20px; font-weight: 600;
}
QPushButton#primaryButton:disabled { background-color: #3a3a45; color: #7a7a85; }
QPushButton { background-color: #33333d; color: #e5e5ea; border: none; border-radius: 8px; padding: 10px 16px; }
QFrame#resultCard { background-color: #26262e; border-radius: 10px; border: 1px solid #33333d; }
QLabel#handleLabel { font-size: 15px; font-weight: 600; color: #f2f2f5; }
QLabel#platformLabel { font-size: 12px; color: #8f8fff; font-weight: 600; }
QLabel#titleLabel { font-size: 13px; color: #d5d5da; }
QLabel#descLabel { font-size: 12px; color: #9a9aa5; }
QLabel#confidenceLabel { font-size: 12px; color: #6fdc8c; margin-top: 4px; }
QLabel#sourceLabel { font-size: 11px; color: #6a6a75; }
QLabel#avatarPlaceholder {
    background-color: #33333d; border-radius: 32px; font-size: 24px; color: #6a6a75;
}
QLabel#summaryLabel { font-size: 12px; color: #7a7a85; padding: 6px 0; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OSINT Finder")
        self.resize(560, 720)
        self.setStyleSheet(STYLESHEET)

        self._manager = SearchManager()
        self._thread = None
        self._worker = None
        self._cards_by_key = {}
        self._search_started_at = 0.0

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel("OSINT Finder")
        title.setObjectName("appTitle")
        root.addWidget(title)

        subtitle = QLabel("Public Username Discovery")
        subtitle.setObjectName("appSubtitle")
        root.addWidget(subtitle)

        self.search_bar = SearchBar()
        self.search_bar.search_requested.connect(self._on_search_requested)
        self.search_bar.cancel_requested.connect(self._on_cancel_requested)
        root.addWidget(self.search_bar)

        self.status_label = QLabel(STATE_MESSAGES[SearchState.IDLE])
        self.status_label.setObjectName("statusLabel")
        root.addWidget(self.status_label)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summaryLabel")
        self.summary_label.setVisible(False)
        root.addWidget(self.summary_label)

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(10)
        self.results_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.results_container)
        scroll.setFrameShape(QScrollArea.NoFrame)
        root.addWidget(scroll, stretch=1)

        self.setCentralWidget(central)

    # -- search lifecycle --------------------------------------------------

    def _on_search_requested(self, username: str, mode: SearchMode, force_refresh: bool):
        self._clear_results()
        self.search_bar.set_searching(True)
        self.summary_label.setVisible(False)
        self._search_started_at = time.monotonic()

        self._thread, self._worker = start_search(
            self._manager,
            username,
            mode,
            force_refresh,
            on_state_changed=self._on_state_changed,
            on_partial_results=self._on_partial_results,
            on_finished=self._on_finished,
        )

    def _on_cancel_requested(self):
        if self._worker:
            self._worker.cancel()
        self.status_label.setText("Cancelling...")

    def _on_state_changed(self, state_value: str, extra: dict):
        state = SearchState(state_value)
        if state == SearchState.DISCOVERY_COMPLETE:
            found = extra.get("found", 0)
            self.status_label.setText(f"{found} profile(s) found")
        elif state == SearchState.ENRICHING:
            count = extra.get("count", 0)
            self.status_label.setText(f"Enriching {count} profile(s)...")
        elif state == SearchState.ERROR:
            self.status_label.setText(extra.get("message") or STATE_MESSAGES[state])
        else:
            self.status_label.setText(STATE_MESSAGES.get(state, ""))

    def _on_partial_results(self, results):
        for result in results:
            self._add_or_update_card(result)

    def _on_finished(self, response: SearchResponse):
        self.search_bar.set_searching(False)

        for result in response.results:
            self._add_or_update_card(result)

        elapsed = time.monotonic() - self._search_started_at
        self.summary_label.setText(
            f"Found: {response.metrics.results_unique}   "
            f"Enriched: {response.metrics.results_enriched}   "
            f"Time: {elapsed:.1f}s"
        )
        self.summary_label.setVisible(True)

        if response.state == SearchState.SUCCESS and not response.results:
            self.status_label.setText(STATE_MESSAGES[SearchState.NO_RESULTS])
        elif response.state in STATE_MESSAGES:
            self.status_label.setText(STATE_MESSAGES[response.state])

        self._retire_thread()

    def _retire_thread(self):
        """Safely release the worker thread once it has actually finished.

        QThread must be joined with wait() before we drop our reference,
        otherwise Qt may destroy it while the underlying OS thread is still
        shutting down.
        """
        thread = self._thread
        self._thread = None
        self._worker = None
        if thread is not None:
            thread.quit()
            thread.wait()

    # -- result cards --------------------------------------------------

    def _add_or_update_card(self, result):
        key = result.dedup_key or f"{result.platform}::{result.profile_url}"
        card = self._cards_by_key.get(key)
        if card is None:
            card = ResultCard(result)
            self._cards_by_key[key] = card
            # insert before the trailing stretch
            self.results_layout.insertWidget(self.results_layout.count() - 1, card)
        else:
            card.update_result(result)

    def _clear_results(self):
        for card in self._cards_by_key.values():
            card.setParent(None)
            card.deleteLater()
        self._cards_by_key = {}

    def closeEvent(self, event):
        if self._worker:
            self._worker.cancel()
        super().closeEvent(event)
