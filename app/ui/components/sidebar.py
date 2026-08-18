from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, QButtonGroup
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from app.ui.icons import get_svg_icon, get_svg_pixmap


class NavButton(QPushButton):
    def __init__(self, text: str, icon_name: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(get_svg_icon(icon_name, normal_color="#94a3b8", active_color="#ffffff", size=18))
        self.setIconSize(QSize(18, 18))
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                color: #94a3b8;
                font-size: 10pt;
                font-weight: 600;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #151822;
                color: #f1f5f9;
            }
            QPushButton:checked {
                background-color: #1e2230;
                color: #ffffff;
                border-left: 3px solid #6366f1;
            }
        """)


class Sidebar(QFrame):
    page_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(210)
        self.setStyleSheet("""
            QFrame#sidebar {
                background-color: #0b0d12;
                border-right: 1px solid #1a1e2b;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 20, 14, 16)
        layout.setSpacing(6)

        # Brand Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        
        logo_label = QLabel(self)
        logo_label.setPixmap(get_svg_pixmap("logo", color="#6366f1", size=24))
        logo_label.setFixedSize(28, 28)
        
        title_label = QLabel("KDownloader", self)
        title_label.setStyleSheet("font-size: 12pt; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;")
        
        subtitle_label = QLabel("Media Downloader Pro", self)
        subtitle_label.setStyleSheet("font-size: 8pt; color: #64748b; font-weight: 500;")

        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        layout.addLayout(header_layout)

        layout.addSpacing(20)

        # Navigation Buttons
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        self.btn_download = NavButton("Téléchargement", "download", self)
        self.btn_history = NavButton("Historique", "history", self)
        self.btn_logs = NavButton("Journaux", "terminal", self)
        self.btn_settings = NavButton("Paramètres", "settings", self)

        self.button_group.addButton(self.btn_download, 0)
        self.button_group.addButton(self.btn_history, 1)
        self.button_group.addButton(self.btn_logs, 2)
        self.button_group.addButton(self.btn_settings, 3)

        self.button_group.idClicked.connect(self.page_changed.emit)

        layout.addWidget(self.btn_download)
        layout.addWidget(self.btn_history)
        layout.addWidget(self.btn_logs)
        layout.addWidget(self.btn_settings)

        layout.addStretch()

        # Version footer
        version_label = QLabel("v2.0.0 • yt-dlp", self)
        version_label.setStyleSheet("font-size: 8pt; color: #475569; text-align: center;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        # Set default active page
        self.btn_download.setChecked(True)

    def set_current_page(self, index: int):
        button = self.button_group.button(index)
        if button:
            button.setChecked(True)
