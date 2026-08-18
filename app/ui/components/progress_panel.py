from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from app.ui.icons import get_svg_icon
from app.ui.theme import get_card_style


class ProgressPanel(QFrame):
    download_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    open_file_requested = pyqtSignal()
    change_folder_requested = pyqtSignal()
    open_folder_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("progress_panel")
        self.setStyleSheet(get_card_style(is_active=False))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Folder destination line
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(8)

        self.folder_icon = QLabel(self)
        self.folder_icon.setPixmap(get_svg_icon("folder", normal_color="#94a3b8", size=16).pixmap(16, 16))
        folder_layout.addWidget(self.folder_icon)

        self.folder_label = QLabel("Dossier: Chargement...", self)
        self.folder_label.setStyleSheet("color: #94a3b8; font-size: 9pt;")
        self.folder_label.setWordWrap(True)
        folder_layout.addWidget(self.folder_label, 1)

        self.btn_change_folder = QPushButton("Modifier", self)
        self.btn_change_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_change_folder.setStyleSheet("padding: 5px 10px; font-size: 8.5pt;")
        self.btn_change_folder.clicked.connect(self.change_folder_requested.emit)
        folder_layout.addWidget(self.btn_change_folder)

        self.btn_open_folder = QPushButton("Ouvrir", self)
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.setIcon(get_svg_icon("folder_open", normal_color="#cbd5e1", size=14))
        self.btn_open_folder.setStyleSheet("padding: 5px 10px; font-size: 8.5pt;")
        self.btn_open_folder.clicked.connect(self.open_folder_requested.emit)
        folder_layout.addWidget(self.btn_open_folder)

        main_layout.addLayout(folder_layout)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Metrics row: Percent | Size | Speed | ETA
        metrics_layout = QHBoxLayout()
        
        self.percent_label = QLabel("0%", self)
        self.percent_label.setStyleSheet("font-weight: 700; color: #6366f1; font-size: 9pt;")
        metrics_layout.addWidget(self.percent_label)

        self.metrics_label = QLabel("En attente...", self)
        self.metrics_label.setStyleSheet("color: #94a3b8; font-size: 9pt;")
        metrics_layout.addWidget(self.metrics_label, 1)

        main_layout.addLayout(metrics_layout)

        # Action Buttons row
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        self.btn_download = QPushButton("Télécharger", self)
        self.btn_download.setObjectName("primary_btn")
        self.btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download.setIcon(get_svg_icon("download", normal_color="#ffffff", size=18))
        self.btn_download.setIconSize(QSize(18, 18))
        self.btn_download.clicked.connect(self.download_requested.emit)
        action_layout.addWidget(self.btn_download, 2)

        self.btn_cancel = QPushButton("Annuler", self)
        self.btn_cancel.setObjectName("danger_btn")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setIcon(get_svg_icon("cancel", normal_color="#f43f5e", size=16))
        self.btn_cancel.setIconSize(QSize(16, 16))
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        action_layout.addWidget(self.btn_cancel, 1)

        self.btn_play = QPushButton("Lire le fichier", self)
        self.btn_play.setObjectName("success_btn")
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.setIcon(get_svg_icon("play", normal_color="#10b981", size=16))
        self.btn_play.setIconSize(QSize(16, 16))
        self.btn_play.setEnabled(False)
        self.btn_play.clicked.connect(self.open_file_requested.emit)
        action_layout.addWidget(self.btn_play, 1)

        main_layout.addLayout(action_layout)

    def set_folder_text(self, path: str):
        self.folder_label.setText(f"Dossier: {path}")

    def set_progress(self, percent: int, metrics_text: str = ""):
        self.progress_bar.setValue(percent)
        self.percent_label.setText(f"{percent}%")
        if metrics_text:
            self.metrics_label.setText(metrics_text)

    def set_downloading_state(self, is_downloading: bool):
        self.btn_download.setEnabled(not is_downloading)
        self.btn_cancel.setEnabled(is_downloading)
        self.btn_change_folder.setEnabled(not is_downloading)
        if is_downloading:
            self.btn_play.setEnabled(False)

    def set_finished_file(self, filename: str):
        self.btn_play.setEnabled(True)
        short_name = filename if len(filename) <= 22 else f"{filename[:20]}..."
        self.btn_play.setText(f"Lire ({short_name})")
