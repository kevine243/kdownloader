from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.ui.components.url_bar import UrlBar
from app.ui.components.media_card import MediaCard
from app.ui.components.format_selector import FormatSelector
from app.ui.components.progress_panel import ProgressPanel


class DownloadView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Responsive Scroll Area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self.layout_content = QVBoxLayout(content)
        self.layout_content.setContentsMargins(20, 20, 20, 20)
        self.layout_content.setSpacing(16)

        # 1. Hero URL Input
        self.url_bar = UrlBar(content)
        self.layout_content.addWidget(self.url_bar)

        # 2. Media Preview Card
        self.media_card = MediaCard(content)
        self.layout_content.addWidget(self.media_card)

        # 3. Format & Options Card
        self.format_selector = FormatSelector(content)
        self.layout_content.addWidget(self.format_selector)

        # 4. Progress & Action Card
        self.progress_panel = ProgressPanel(content)
        self.layout_content.addWidget(self.progress_panel)

        self.layout_content.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def set_downloading_state(self, is_downloading: bool):
        self.url_bar.set_enabled(not is_downloading)
        self.media_card.refresh_btn.setEnabled(not is_downloading)
        self.format_selector.set_enabled(not is_downloading)
        self.progress_panel.set_downloading_state(is_downloading)
