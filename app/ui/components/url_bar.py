from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QApplication
)
from PyQt6.QtCore import pyqtSignal, QTimer, QSize, Qt
from app.ui.icons import get_svg_icon


class UrlBar(QWidget):
    url_submitted = pyqtSignal(str)
    url_auto_detected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_inspected_url = ""

        # Auto-fetch debounce timer
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(600)
        self.debounce_timer.timeout.connect(self._on_debounce_timeout)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Collez l'URL de la vidéo ou de la playlist YouTube, Twitch, etc...")
        self.input_field.textChanged.connect(self._on_text_changed)
        self.input_field.returnPressed.connect(self._on_return_pressed)
        layout.addWidget(self.input_field, 1)

        self.paste_btn = QPushButton("Coller", self)
        self.paste_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.paste_btn.setIcon(get_svg_icon("paste", normal_color="#cbd5e1", size=16))
        self.paste_btn.setIconSize(QSize(16, 16))
        self.paste_btn.setToolTip("Coller depuis le presse-papier et analyser automatiquement")
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        layout.addWidget(self.paste_btn)

    def text(self) -> str:
        return self.input_field.text().strip()

    def setText(self, text: str):
        self.input_field.setText(text)

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.input_field.setText(text)
            self._trigger_auto_fetch(text)

    def _on_text_changed(self, text: str):
        cleaned = text.strip()
        if (cleaned.startswith("http://") or cleaned.startswith("https://")) and cleaned != self.last_inspected_url:
            self.debounce_timer.start()

    def _on_debounce_timeout(self):
        url = self.text()
        self._trigger_auto_fetch(url)

    def _trigger_auto_fetch(self, url: str):
        if url and (url.startswith("http://") or url.startswith("https://")) and url != self.last_inspected_url:
            self.last_inspected_url = url
            self.url_auto_detected.emit(url)

    def _on_return_pressed(self):
        url = self.text()
        if url:
            self.url_submitted.emit(url)

    def set_enabled(self, enabled: bool):
        self.input_field.setEnabled(enabled)
        self.paste_btn.setEnabled(enabled)
