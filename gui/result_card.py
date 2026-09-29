"""Compact result card for a single SearchResult."""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from core.models import SearchResult

AVATAR_SIZE = 64


class ResultCard(QFrame):
    def __init__(self, result: SearchResult, parent=None):
        super().__init__(parent)
        self.result = result
        self.setObjectName("resultCard")
        self.setFrameShape(QFrame.StyledPanel)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(AVATAR_SIZE, AVATAR_SIZE)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setObjectName("avatarPlaceholder")
        self._set_avatar(self.result.avatar_path)
        layout.addWidget(self.avatar_label)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        handle_label = QLabel(f"@{self.result.username}")
        handle_label.setObjectName("handleLabel")
        info_col.addWidget(handle_label)

        platform_label = QLabel(self.result.platform)
        platform_label.setObjectName("platformLabel")
        info_col.addWidget(platform_label)

        if self.result.title:
            title_label = QLabel(self.result.title)
            title_label.setObjectName("titleLabel")
            info_col.addWidget(title_label)

        if self.result.description:
            desc_label = QLabel(self.result.description)
            desc_label.setObjectName("descLabel")
            desc_label.setWordWrap(True)
            info_col.addWidget(desc_label)

        confidence_label = QLabel(
            f"Relevance: {self.result.confidence}% ({self.result.confidence_label.value})"
        )
        confidence_label.setObjectName("confidenceLabel")
        info_col.addWidget(confidence_label)

        source_label = QLabel(f"Source: {', '.join(self.result.source_engines) or 'unknown'}")
        source_label.setObjectName("sourceLabel")
        info_col.addWidget(source_label)

        layout.addLayout(info_col, stretch=1)

        open_button = QPushButton("Open Profile")
        open_button.clicked.connect(self._open_profile)
        layout.addWidget(open_button, alignment=Qt.AlignTop)

    def _set_avatar(self, avatar_path):
        if avatar_path:
            pixmap = QPixmap(avatar_path)
            if not pixmap.isNull():
                self.avatar_label.setPixmap(
                    pixmap.scaled(AVATAR_SIZE, AVATAR_SIZE, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                )
                return
        self.avatar_label.setText("👤")

    def update_result(self, result: SearchResult):
        """Called when enrichment completes for this card's result."""
        self.result = result
        self._set_avatar(result.avatar_path)

    def _open_profile(self):
        webbrowser.open(self.result.profile_url)
