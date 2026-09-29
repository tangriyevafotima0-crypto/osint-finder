"""Username input + Fast/Deep mode selector + Search/Cancel button."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from core.models import SearchMode


class SearchBar(QWidget):
    search_requested = Signal(str, object, bool)  # username, SearchMode, force_refresh
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._searching = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        label = QLabel("Username")
        label.setObjectName("fieldLabel")
        layout.addWidget(label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("e.g. john_smith or @john_smith")
        self.username_input.returnPressed.connect(self._on_search_clicked)
        layout.addWidget(self.username_input)

        mode_row = QHBoxLayout()
        self.fast_radio = QRadioButton("Fast Search")
        self.deep_radio = QRadioButton("Deep Search")
        self.fast_radio.setChecked(True)
        mode_row.addWidget(self.fast_radio)
        mode_row.addWidget(self.deep_radio)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        button_row = QHBoxLayout()
        self.search_button = QPushButton("🔍  Search")
        self.search_button.setObjectName("primaryButton")
        self.search_button.clicked.connect(self._on_search_clicked)
        button_row.addWidget(self.search_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setEnabled(False)
        self.refresh_button.clicked.connect(self._on_refresh_clicked)
        button_row.addWidget(self.refresh_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        button_row.addWidget(self.cancel_button)

        button_row.addStretch()
        layout.addLayout(button_row)

    def _current_mode(self) -> SearchMode:
        return SearchMode.DEEP if self.deep_radio.isChecked() else SearchMode.FAST

    def _on_search_clicked(self):
        username = self.username_input.text().strip()
        if not username:
            return
        self.search_requested.emit(username, self._current_mode(), False)

    def _on_refresh_clicked(self):
        username = self.username_input.text().strip()
        if not username:
            return
        self.search_requested.emit(username, self._current_mode(), True)

    def set_searching(self, is_searching: bool):
        self._searching = is_searching
        self.search_button.setEnabled(not is_searching)
        self.refresh_button.setEnabled(not is_searching)
        self.cancel_button.setVisible(is_searching)
