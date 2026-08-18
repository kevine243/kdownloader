from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from app.ui.icons import get_svg_icon


class LogView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        title_layout = QVBoxLayout()
        title_label = QLabel("Journaux d'Exécution", self)
        title_label.setStyleSheet("font-size: 13pt; font-weight: 700; color: #ffffff;")
        subtitle_label = QLabel("Sortie détaillée et diagnostics du moteur yt-dlp", self)
        subtitle_label.setStyleSheet("font-size: 8.5pt; color: #64748b;")
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        self.btn_copy = QPushButton("Copier", self)
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setIcon(get_svg_icon("paste", normal_color="#94a3b8", size=14))
        self.btn_copy.setStyleSheet("padding: 6px 12px; font-size: 9pt;")
        self.btn_copy.clicked.connect(self.copy_logs)
        header_layout.addWidget(self.btn_copy)

        self.btn_clear = QPushButton("Effacer", self)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setIcon(get_svg_icon("trash", normal_color="#94a3b8", size=14))
        self.btn_clear.setStyleSheet("padding: 6px 12px; font-size: 9pt;")
        self.btn_clear.clicked.connect(self.clear_logs)
        header_layout.addWidget(self.btn_clear)

        layout.addLayout(header_layout)

        # Console Text Box
        self.console = QTextEdit(self)
        self.console.setObjectName("log_console")
        self.console.setReadOnly(True)
        layout.addWidget(self.console, 1)

    def append_log(self, text: str):
        self.console.append(text)
        # Auto scroll to bottom
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_logs(self):
        self.console.clear()

    def copy_logs(self):
        text = self.console.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
