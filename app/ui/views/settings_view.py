import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFileDialog, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from app.ui.icons import get_svg_icon, get_svg_pixmap
from app.ui.theme import get_card_style
from app.config import AppConfig
from app.core.ffmpeg import get_ffmpeg_path, is_ffmpeg_available
from app.core.ytdlp import check_yt_dlp


class SettingsView(QWidget):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        title_layout = QVBoxLayout()
        title_label = QLabel("Paramètres & Diagnostics", self)
        title_label.setStyleSheet("font-size: 13pt; font-weight: 700; color: #ffffff;")
        subtitle_label = QLabel("Configurez le comportement de l'application et vérifiez vos dépendances", self)
        subtitle_label.setStyleSheet("font-size: 8.5pt; color: #64748b;")
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        layout.addLayout(title_layout)

        # 1. Download Folder Card
        folder_card = QFrame(self)
        folder_card.setStyleSheet(get_card_style())
        folder_layout = QVBoxLayout(folder_card)
        folder_layout.setContentsMargins(14, 14, 14, 14)
        folder_layout.setSpacing(8)

        card1_title = QLabel("Dossier de Téléchargement par Défaut", folder_card)
        card1_title.setStyleSheet("font-weight: 700; color: #f1f5f9;")
        folder_layout.addWidget(card1_title)

        f_row = QHBoxLayout()
        self.folder_path_lbl = QLabel(self.config.download_path, folder_card)
        self.folder_path_lbl.setStyleSheet("color: #94a3b8; font-size: 9.5pt;")
        self.folder_path_lbl.setWordWrap(True)
        f_row.addWidget(self.folder_path_lbl, 1)

        self.btn_browse = QPushButton("Modifier", folder_card)
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.clicked.connect(self.select_folder)
        f_row.addWidget(self.btn_browse)

        self.btn_open = QPushButton("Ouvrir", folder_card)
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.setIcon(get_svg_icon("folder_open", normal_color="#cbd5e1", size=14))
        self.btn_open.clicked.connect(self.open_folder)
        f_row.addWidget(self.btn_open)

        folder_layout.addLayout(f_row)
        layout.addWidget(folder_card)

        # 2. General Preferences Card
        pref_card = QFrame(self)
        pref_card.setStyleSheet(get_card_style())
        pref_layout = QVBoxLayout(pref_card)
        pref_layout.setContentsMargins(14, 14, 14, 14)
        pref_layout.setSpacing(10)

        card2_title = QLabel("Préférences Générales", pref_card)
        card2_title.setStyleSheet("font-weight: 700; color: #f1f5f9;")
        pref_layout.addWidget(card2_title)

        self.check_auto_fetch = QCheckBox("Analyser automatiquement les URLs collées", pref_card)
        self.check_auto_fetch.setChecked(self.config.auto_fetch_metadata)
        self.check_auto_fetch.toggled.connect(lambda v: setattr(self.config, "auto_fetch_metadata", v))
        pref_layout.addWidget(self.check_auto_fetch)

        layout.addWidget(pref_card)

        # 3. System Diagnostics Card
        diag_card = QFrame(self)
        diag_card.setStyleSheet(get_card_style())
        diag_layout = QVBoxLayout(diag_card)
        diag_layout.setContentsMargins(14, 14, 14, 14)
        diag_layout.setSpacing(10)

        card3_title = QLabel("Diagnostics Système", diag_card)
        card3_title.setStyleSheet("font-weight: 700; color: #f1f5f9;")
        diag_layout.addWidget(card3_title)

        # yt-dlp Status
        ytdlp_ok, ytdlp_ver = check_yt_dlp()
        ytdlp_row = QHBoxLayout()
        ytdlp_icon = QLabel(diag_card)
        ytdlp_icon.setPixmap(get_svg_pixmap("check" if ytdlp_ok else "cancel", color="#10b981" if ytdlp_ok else "#f43f5e", size=16))
        ytdlp_row.addWidget(ytdlp_icon)

        ytdlp_text = f"yt-dlp : {'Installé (version ' + ytdlp_ver + ')' if ytdlp_ok else 'Non détecté'}"
        ytdlp_lbl = QLabel(ytdlp_text, diag_card)
        ytdlp_lbl.setStyleSheet(f"color: {'#10b981' if ytdlp_ok else '#f43f5e'}; font-weight: 500;")
        ytdlp_row.addWidget(ytdlp_lbl, 1)
        diag_layout.addLayout(ytdlp_row)

        # FFmpeg Status
        ffmpeg_ok = is_ffmpeg_available()
        ffmpeg_path = get_ffmpeg_path()
        ffmpeg_row = QHBoxLayout()
        ffmpeg_icon = QLabel(diag_card)
        ffmpeg_icon.setPixmap(get_svg_pixmap("check" if ffmpeg_ok else "cancel", color="#10b981" if ffmpeg_ok else "#f43f5e", size=16))
        ffmpeg_row.addWidget(ffmpeg_icon)

        ffmpeg_text = f"FFmpeg : {'Disponible (' + ffmpeg_path + ')' if ffmpeg_ok else 'Non détecté (conversion audio réduite)'}"
        ffmpeg_lbl = QLabel(ffmpeg_text, diag_card)
        ffmpeg_lbl.setStyleSheet(f"color: {'#10b981' if ffmpeg_ok else '#f43f5e'}; font-weight: 500;")
        ffmpeg_lbl.setWordWrap(True)
        ffmpeg_row.addWidget(ffmpeg_lbl, 1)
        diag_layout.addLayout(ffmpeg_row)

        layout.addWidget(diag_card)

        layout.addStretch()

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier de destination", self.config.download_path)
        if folder:
            self.config.download_path = folder
            self.folder_path_lbl.setText(folder)

    def open_folder(self):
        path = self.config.download_path
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(self, "Erreur", "Le dossier spécifié n'existe pas.")
