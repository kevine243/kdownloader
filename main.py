import sys
import os
import re
import json
import shutil
import threading
import subprocess
import time
import urllib.request
import psutil
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QPushButton, QLabel, QFileDialog, QRadioButton,
    QComboBox, QCheckBox, QMessageBox, QTextEdit, QProgressBar,
    QGroupBox, QTabWidget, QListWidget, QListWidgetItem, QFrame,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import (
    pyqtSignal, QObject, QSettings, Qt, QUrl, QTimer, QStandardPaths,
    QSize
)
from PyQt6.QtGui import (
    QIcon, QDesktopServices, QFont, QPixmap, QImage, QColor, QKeySequence,
    QShortcut
)


def get_ffmpeg_path():
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and os.path.exists(path):
            return path
    except Exception:
        pass
    return None


def get_base_yt_dlp_cmd():
    cmd = ["yt-dlp", "--extractor-args", "youtube:player_client=web_embedded,android_vr,mweb,web"]
    if shutil.which("node"):
        cmd += ["--js-runtimes", "node", "--remote-components", "ejs:github"]
    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path:
        cmd += ["--ffmpeg-location", ffmpeg_path]
    return cmd


def format_duration(seconds):
    if not seconds or seconds < 0:
        return "00:00"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_bytes_human(b):
    if not b or b <= 0:
        return ""
    if b < 1024 * 1024:
        return f" (~{b / 1024:.1f} KB)"
    elif b < 1024 * 1024 * 1024:
        return f" (~{b / (1024 * 1024):.1f} MB)"
    else:
        return f" (~{b / (1024 * 1024 * 1024):.2f} GB)"


class Communicate(QObject):
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    file_info_signal = pyqtSignal(str)
    download_state_signal = pyqtSignal(bool)
    qualities_signal = pyqtSignal(list)
    metadata_signal = pyqtSignal(dict)
    finished_file_signal = pyqtSignal(str)


class KDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.communicate = Communicate()
        self.communicate.update_signal.connect(self.update_output)
        self.communicate.progress_signal.connect(self.update_progress)
        self.communicate.file_info_signal.connect(self.update_file_info)
        self.communicate.download_state_signal.connect(self.set_ui_downloading)
        self.communicate.qualities_signal.connect(self.update_qualities)
        self.communicate.metadata_signal.connect(self.display_metadata)
        self.communicate.finished_file_signal.connect(self.on_download_finished_file)

        self.downloading = False
        self.download_path = ""
        self.download_process = None
        self.last_downloaded_file = None
        self.current_preview_url = ""

        # Timer pour auto-fetch détection de lien (anti-rebond)
        self.auto_fetch_timer = QTimer()
        self.auto_fetch_timer.setSingleShot(True)
        self.auto_fetch_timer.setInterval(600)
        self.auto_fetch_timer.timeout.connect(self.auto_inspect_url)

        self.settings = QSettings("KDownloader", "App")
        
        self.init_ui()
        self.load_settings()
        self.load_history()
        self.load_icon()
        self.setup_shortcuts()

        # Activer le Drag & Drop
        self.setAcceptDrops(True)

    def load_icon(self):
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "icon.png"),
            os.path.join(os.path.dirname(__file__), "assets", "icon.png"),
            os.path.join(os.path.dirname(__file__), "icon.ico"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                self.setWindowIcon(QIcon(path))
                break

    def load_settings(self):
        saved_path = self.settings.value("download_path", "")
        if saved_path and os.path.exists(saved_path):
            self.download_path = saved_path
        else:
            # Dossier Téléchargements par défaut
            default_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
            if not default_path or not os.path.exists(default_path):
                default_path = os.path.expanduser("~/Downloads")
            self.download_path = default_path
            self.settings.setValue("download_path", self.download_path)

        self.destination_label.setText(f"Dossier: {self.download_path}")

    def load_history(self):
        try:
            history_data = self.settings.value("download_history", "[]")
            items = json.loads(history_data)
            self.history_list.clear()
            for item in items:
                self.add_history_item_to_ui(item)
        except Exception:
            pass

    def save_history_item(self, item):
        try:
            history_data = self.settings.value("download_history", "[]")
            items = json.loads(history_data)
            items.insert(0, item)
            # Limiter à 50 éléments
            items = items[:50]
            self.settings.setValue("download_history", json.dumps(items))
            self.add_history_item_to_ui(item, prepend=True)
        except Exception:
            pass

    def setup_shortcuts(self):
        # Échap pour annuler
        cancel_shortcut = QShortcut(QKeySequence("Escape"), self)
        cancel_shortcut.activated.connect(self.handle_escape)

    def handle_escape(self):
        if self.downloading:
            self.cancel_download()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() or event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        text = ""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                text = urls[0].toString()
        elif event.mimeData().hasText():
            text = event.mimeData().text()

        text = text.strip()
        if text.startswith("http://") or text.startswith("https://"):
            self.url_input.setText(text)
            event.acceptProposedAction()

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #313244;
                background-color: #1e1e2e;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #181825;
                color: #a6adc8;
                padding: 8px 18px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #313244;
                color: #89b4fa;
                border-bottom: 2px solid #89b4fa;
            }
            QTabBar::tab:hover:!selected {
                background-color: #25263a;
                color: #cdd6f4;
            }
            QGroupBox {
                border: 1px solid #45475a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 12px;
                font-weight: bold;
                color: #89b4fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: #1e1e2e;
            }
            QLineEdit, QComboBox, QTextEdit, QListWidget {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                color: #cdd6f4;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QListWidget:focus {
                border: 1px solid #89b4fa;
            }
            QPushButton {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 7px 13px;
                color: #cdd6f4;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45475a;
                border-color: #89b4fa;
            }
            QPushButton:pressed {
                background-color: #585b70;
            }
            QPushButton:disabled {
                background-color: #181825;
                color: #585b70;
                border-color: #313244;
            }
            QPushButton#download_btn {
                background-color: #89b4fa;
                color: #11111b;
                border: none;
                font-size: 11pt;
                padding: 9px;
            }
            QPushButton#download_btn:hover {
                background-color: #b4befe;
            }
            QPushButton#download_btn:disabled {
                background-color: #45475a;
                color: #7f849c;
            }
            QPushButton#cancel_btn {
                background-color: #f38ba8;
                color: #11111b;
                border: none;
                font-size: 11pt;
                padding: 9px;
            }
            QPushButton#cancel_btn:hover {
                background-color: #f5e0dc;
            }
            QPushButton#cancel_btn:disabled {
                background-color: #45475a;
                color: #7f849c;
            }
            QPushButton#play_btn {
                background-color: #a6e3a1;
                color: #11111b;
                border: none;
            }
            QPushButton#play_btn:hover {
                background-color: #94e2d5;
            }
            QPushButton#paste_btn {
                background-color: #45475a;
                border: 1px solid #585b70;
            }
            QPushButton#paste_btn:hover {
                background-color: #585b70;
            }
            QProgressBar {
                border: 1px solid #45475a;
                border-radius: 6px;
                text-align: center;
                background-color: #313244;
                color: #cdd6f4;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 5px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #181825;
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #45475a;
                min-height: 25px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #585b70;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QRadioButton {
                spacing: 8px;
                color: #cdd6f4;
                font-weight: bold;
                font-size: 10pt;
                padding: 4px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #585b70;
                background-color: #1e1e2e;
            }
            QRadioButton::indicator:hover {
                border-color: #89b4fa;
            }
            QRadioButton::indicator:checked {
                border-color: #89b4fa;
                background-color: #89b4fa;
            }
            QCheckBox {
                spacing: 8px;
                color: #cdd6f4;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 2px solid #585b70;
                background-color: #1e1e2e;
            }
            QCheckBox::indicator:checked {
                border-color: #89b4fa;
                background-color: #89b4fa;
            }
            QLabel {
                color: #cdd6f4;
            }
            QFrame#preview_card {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 8px;
            }
        """)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.tab_widget = QTabWidget(self)

        # Onglet 1: Téléchargement avec ScrollArea responsive
        download_tab = QWidget()
        download_tab_layout = QVBoxLayout(download_tab)
        download_tab_layout.setContentsMargins(0, 0, 0, 0)
        download_tab_layout.setSpacing(0)

        scroll_area = QScrollArea(download_tab)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(10, 10, 10, 10)

        # --- Groupe 1: URL & Destination ---
        source_group = QGroupBox("Source && Destination")
        source_layout = QVBoxLayout()

        url_input_layout = QHBoxLayout()
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Collez l'URL de la vidéo ou de la playlist ici...")
        self.url_input.textChanged.connect(self.on_url_text_changed)
        self.url_input.returnPressed.connect(self.on_url_return_pressed)
        url_input_layout.addWidget(self.url_input)

        self.paste_btn = QPushButton("📋 Coller", self)
        self.paste_btn.setObjectName("paste_btn")
        self.paste_btn.setToolTip("Coller depuis le presse-papier et analyser automatiquement")
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        url_input_layout.addWidget(self.paste_btn)

        source_layout.addLayout(url_input_layout)

        folder_layout = QHBoxLayout()
        self.destination_label = QLabel("Dossier: Chargement...", self)
        self.destination_label.setWordWrap(True)
        folder_layout.addWidget(self.destination_label, 1)

        self.select_folder_btn = QPushButton("📁 Choisir un dossier", self)
        self.select_folder_btn.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.select_folder_btn)

        self.open_folder_btn = QPushButton("📂 Ouvrir le dossier", self)
        self.open_folder_btn.clicked.connect(self.open_folder)
        folder_layout.addWidget(self.open_folder_btn)

        source_layout.addLayout(folder_layout)
        source_group.setLayout(source_layout)
        scroll_layout.addWidget(source_group)

        # --- Carte d'aperçu dynamique (Thumbnail + Titre + Durée) ---
        self.preview_frame = QFrame(self)
        self.preview_frame.setObjectName("preview_card")
        preview_layout = QHBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.setSpacing(12)

        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setFixedSize(130, 75)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet("background-color: #11111b; border-radius: 6px; color: #6c7086;")
        self.thumbnail_label.setText("Pas d'aperçu")
        preview_layout.addWidget(self.thumbnail_label)

        info_meta_layout = QVBoxLayout()
        info_meta_layout.setSpacing(3)
        self.title_label = QLabel("Titre de la vidéo : En attente d'un lien...", self)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 10.5pt; color: #89b4fa;")
        self.title_label.setWordWrap(True)
        info_meta_layout.addWidget(self.title_label)

        self.channel_duration_label = QLabel("Chaîne : -  |  Durée : -", self)
        self.channel_duration_label.setStyleSheet("color: #a6adc8; font-size: 9pt;")
        info_meta_layout.addWidget(self.channel_duration_label)

        self.status_badge_label = QLabel("ℹ️ Entrez une URL pour prévisualiser", self)
        self.status_badge_label.setStyleSheet("color: #94e2d5; font-size: 8.5pt;")
        info_meta_layout.addWidget(self.status_badge_label)
        info_meta_layout.addStretch()

        preview_layout.addLayout(info_meta_layout, 1)
        scroll_layout.addWidget(self.preview_frame)

        # --- Groupe 2: Options de Téléchargement (Deux Cartes Visibles) ---
        options_group = QGroupBox("Options de Téléchargement")
        options_layout = QVBoxLayout()
        options_layout.setSpacing(8)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        # Carte 1: Vidéo
        self.video_card = QFrame(self)
        self.video_card.setObjectName("video_card")
        self.video_card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.video_card.mousePressEvent = lambda e: self.video_radio.setChecked(True)
        video_card_layout = QVBoxLayout(self.video_card)
        video_card_layout.setContentsMargins(10, 10, 10, 10)
        video_card_layout.setSpacing(8)

        self.video_radio = QRadioButton("🎥 Format Vidéo", self)
        self.video_radio.setChecked(True)
        self.video_radio.toggled.connect(self.on_format_radio_toggled)
        video_card_layout.addWidget(self.video_radio)

        self.video_quality_label = QLabel("Qualité Vidéo :", self)
        self.quality_select = QComboBox(self)
        self.quality_select.addItems([
            "Meilleure qualité", "4K (2160p)", "2K (1440p)",
            "1080p", "720p", "480p", "360p"
        ])
        video_card_layout.addWidget(self.video_quality_label)
        video_card_layout.addWidget(self.quality_select)

        self.subtitles_checkbox = QCheckBox("💬 Sous-titres (FR/EN)", self)
        self.split_chapters_checkbox = QCheckBox("✂️ Découper en chapitres", self)
        video_card_layout.addWidget(self.subtitles_checkbox)
        video_card_layout.addWidget(self.split_chapters_checkbox)
        video_card_layout.addStretch()

        cards_layout.addWidget(self.video_card, 1)

        # Carte 2: Audio
        self.audio_card = QFrame(self)
        self.audio_card.setObjectName("audio_card")
        self.audio_card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.audio_card.mousePressEvent = lambda e: self.audio_radio.setChecked(True)
        audio_card_layout = QVBoxLayout(self.audio_card)
        audio_card_layout.setContentsMargins(10, 10, 10, 10)
        audio_card_layout.setSpacing(8)

        self.audio_radio = QRadioButton("🎵 Audio Uniquement", self)
        self.audio_radio.setChecked(False)
        self.audio_radio.toggled.connect(self.on_format_radio_toggled)
        audio_card_layout.addWidget(self.audio_radio)

        self.audio_format_label = QLabel("Format Audio :", self)
        self.audio_format_select = QComboBox(self)
        self.audio_format_select.addItems(["MP3", "M4A", "FLAC", "WAV", "OPUS"])
        audio_card_layout.addWidget(self.audio_format_label)
        audio_card_layout.addWidget(self.audio_format_select)

        self.audio_bitrate_label = QLabel("Débit / Qualité :", self)
        self.audio_bitrate_select = QComboBox(self)
        self.audio_bitrate_select.addItems([
            "Meilleure qualité (V0 / ~320k)",
            "320 kbps (CBR)",
            "256 kbps",
            "192 kbps (Standard)",
            "128 kbps (Éco)"
        ])
        audio_card_layout.addWidget(self.audio_bitrate_label)
        audio_card_layout.addWidget(self.audio_bitrate_select)

        self.embed_metadata_checkbox = QCheckBox("🏷️ Pochette & Métadonnées", self)
        self.embed_metadata_checkbox.setChecked(True)
        audio_card_layout.addWidget(self.embed_metadata_checkbox)
        audio_card_layout.addStretch()

        cards_layout.addWidget(self.audio_card, 1)

        options_layout.addLayout(cards_layout)

        # Plage Playlist
        playlist_range_layout = QHBoxLayout()
        playlist_range_label = QLabel("Plage playlist (optionnel) :", self)
        self.playlist_range_input = QLineEdit(self)
        self.playlist_range_input.setPlaceholderText("ex: 1-5, 8 ou laisser vide pour tout")
        playlist_range_layout.addWidget(playlist_range_label)
        playlist_range_layout.addWidget(self.playlist_range_input)
        options_layout.addLayout(playlist_range_layout)

        # Boutons d'inspection manuelle
        inspect_layout = QHBoxLayout()
        self.check_playlist_btn = QPushButton("📑 Playlist", self)
        self.check_playlist_btn.clicked.connect(self.check_playlist)
        inspect_layout.addWidget(self.check_playlist_btn)

        self.check_chapters_btn = QPushButton("📖 Chapitres", self)
        self.check_chapters_btn.clicked.connect(self.check_chapters)
        inspect_layout.addWidget(self.check_chapters_btn)

        self.check_qualities_btn = QPushButton("🔍 Actualiser infos", self)
        self.check_qualities_btn.clicked.connect(lambda: self.inspect_url_thread(force_msg=True))
        inspect_layout.addWidget(self.check_qualities_btn)

        options_layout.addLayout(inspect_layout)

        options_group.setLayout(options_layout)
        scroll_layout.addWidget(options_group)

        # Mettre en surbrillance le mode initial
        self.set_active_mode_highlight(True)

        # --- Groupe 3: Action, Logs & Progression ---
        status_group = QGroupBox("Progression && Journaux")
        status_layout = QVBoxLayout()
        status_layout.setSpacing(6)

        action_layout = QHBoxLayout()
        self.download_btn = QPushButton("🚀 Télécharger", self)
        self.download_btn.setObjectName("download_btn")
        self.download_btn.clicked.connect(self.start_download)
        action_layout.addWidget(self.download_btn, 2)

        self.cancel_btn = QPushButton("⏹️ Annuler", self)
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_download)
        action_layout.addWidget(self.cancel_btn, 1)

        self.play_btn = QPushButton("▶️ Lire le fichier", self)
        self.play_btn.setObjectName("play_btn")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.open_last_downloaded_file)
        action_layout.addWidget(self.play_btn, 1)

        status_layout.addLayout(action_layout)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar)

        self.file_info_label = QLabel("", self)
        self.file_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_info_label.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        status_layout.addWidget(self.file_info_label)

        log_header_layout = QHBoxLayout()
        log_header_label = QLabel("Journal d'exécution :", self)
        log_header_layout.addWidget(log_header_label)
        log_header_layout.addStretch()

        self.clear_logs_btn = QPushButton("🧹 Effacer", self)
        self.clear_logs_btn.clicked.connect(lambda: self.download_info.clear())
        log_header_layout.addWidget(self.clear_logs_btn)
        status_layout.addLayout(log_header_layout)

        self.download_info = QTextEdit(self)
        self.download_info.setReadOnly(True)
        self.download_info.setMinimumHeight(100)
        status_layout.addWidget(self.download_info)

        status_group.setLayout(status_layout)
        scroll_layout.addWidget(status_group)

        scroll_area.setWidget(scroll_content)
        download_tab_layout.addWidget(scroll_area)

        self.tab_widget.addTab(download_tab, "📥 Téléchargement")

        # Onglet 2: Historique
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_layout.setSpacing(8)
        history_layout.setContentsMargins(8, 8, 8, 8)

        history_header_layout = QHBoxLayout()
        history_label = QLabel("Historique des téléchargements récents :", self)
        history_header_layout.addWidget(history_label)
        history_header_layout.addStretch()

        self.clear_history_btn = QPushButton("🗑️ Effacer l'historique", self)
        self.clear_history_btn.clicked.connect(self.clear_history)
        history_header_layout.addWidget(self.clear_history_btn)
        history_layout.addLayout(history_header_layout)

        self.history_list = QListWidget(self)
        self.history_list.itemDoubleClicked.connect(self.on_history_item_double_clicked)
        history_layout.addWidget(self.history_list)

        history_actions_layout = QHBoxLayout()
        self.open_history_file_btn = QPushButton("▶️ Ouvrir le fichier sélectionné", self)
        self.open_history_file_btn.clicked.connect(self.open_selected_history_file)
        history_actions_layout.addWidget(self.open_history_file_btn)

        self.open_history_folder_btn = QPushButton("📂 Ouvrir dans le dossier", self)
        self.open_history_folder_btn.clicked.connect(self.open_selected_history_folder)
        history_actions_layout.addWidget(self.open_history_folder_btn)

        history_layout.addLayout(history_actions_layout)

        self.tab_widget.addTab(history_tab, "🕒 Historique")

        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
        self.setWindowTitle("KDownloader - yt-dlp GUI Pro")
        self.setMinimumSize(540, 480)
        self.resize(680, 750)
        self.apply_stylesheet()

    def set_active_mode_highlight(self, is_video: bool):
        if is_video:
            self.video_card.setProperty("active", "true")
            self.audio_card.setProperty("active", "false")
            self.video_card.setStyleSheet("""
                QFrame#video_card {
                    background-color: #24273a;
                    border: 2px solid #89b4fa;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            self.audio_card.setStyleSheet("""
                QFrame#audio_card {
                    background-color: #181825;
                    border: 1px solid #313244;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            self.video_quality_label.setEnabled(True)
            self.quality_select.setEnabled(True)
            self.subtitles_checkbox.setEnabled(True)
            self.split_chapters_checkbox.setEnabled(True)

            self.audio_format_label.setEnabled(False)
            self.audio_format_select.setEnabled(False)
            self.audio_bitrate_label.setEnabled(False)
            self.audio_bitrate_select.setEnabled(False)
        else:
            self.video_card.setProperty("active", "false")
            self.audio_card.setProperty("active", "true")
            self.video_card.setStyleSheet("""
                QFrame#video_card {
                    background-color: #181825;
                    border: 1px solid #313244;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            self.audio_card.setStyleSheet("""
                QFrame#audio_card {
                    background-color: #24273a;
                    border: 2px solid #a6e3a1;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            self.video_quality_label.setEnabled(False)
            self.quality_select.setEnabled(False)
            self.subtitles_checkbox.setEnabled(False)
            self.split_chapters_checkbox.setEnabled(False)

            self.audio_format_label.setEnabled(True)
            self.audio_format_select.setEnabled(True)
            self.audio_bitrate_label.setEnabled(True)
            self.audio_bitrate_select.setEnabled(True)

    def on_format_radio_toggled(self):
        self.set_active_mode_highlight(self.video_radio.isChecked())

    def on_url_text_changed(self, text):
        cleaned = text.strip()
        if (cleaned.startswith("http://") or cleaned.startswith("https://")) and cleaned != self.current_preview_url:
            self.auto_fetch_timer.start()

    def on_url_return_pressed(self):
        if not self.downloading:
            self.start_download()

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.url_input.setText(text)
            self.auto_inspect_url()

    def auto_inspect_url(self):
        url = self.url_input.text().strip()
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return
        if url == self.current_preview_url:
            return
        self.inspect_url_thread(force_msg=False)

    def inspect_url_thread(self, force_msg=False):
        url = self.url_input.text().strip()
        if not url:
            if force_msg:
                QMessageBox.warning(self, "Erreur", "Veuillez entrer une URL valide.")
            return

        if not self.check_yt_dlp():
            return

        self.status_badge_label.setText("⏳ Analyse des métadonnées et miniature...")
        if force_msg:
            self.communicate.update_signal.emit("⏳ Analyse détaillée en cours...")

        thread = threading.Thread(target=self.fetch_metadata_worker, args=(url, force_msg), daemon=True)
        thread.start()

    def fetch_metadata_worker(self, url, force_msg):
        cmd = get_base_yt_dlp_cmd() + ["--dump-single-json", "--flat-playlist", url]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            self.current_preview_url = url
            title = data.get("title", "Sans titre")
            uploader = data.get("uploader") or data.get("channel") or data.get("artist") or "Inconnu"
            duration = data.get("duration", 0)
            thumbnail_url = data.get("thumbnail") or ""
            
            # Formats & Qualités
            qualities, available_names = self.parse_available_qualities(data)

            # Télécharger la miniature
            thumb_bytes = None
            if thumbnail_url:
                try:
                    req = urllib.request.Request(
                        thumbnail_url,
                        headers={"User-Agent": "Mozilla/5.0"}
                    )
                    with urllib.request.urlopen(req, timeout=5) as response:
                        thumb_bytes = response.read()
                except Exception:
                    pass

            _type = data.get("_type")
            entries = data.get("entries")
            is_playlist = (_type in ("playlist", "multi_video") or isinstance(entries, list))
            count = len(entries) if entries is not None else data.get("playlist_count", 0)

            metadata = {
                "title": title,
                "uploader": uploader,
                "duration_str": format_duration(duration),
                "thumbnail_bytes": thumb_bytes,
                "qualities": qualities,
                "available_names": available_names,
                "is_playlist": is_playlist,
                "count": count,
                "force_msg": force_msg
            }
            self.communicate.metadata_signal.emit(metadata)

        except Exception as e:
            if force_msg:
                self.communicate.update_signal.emit(f"❌ Erreur lors de l'analyse : {str(e)}")

    def display_metadata(self, meta):
        title = meta.get("title", "Sans titre")
        uploader = meta.get("uploader", "Inconnu")
        duration_str = meta.get("duration_str", "00:00")
        is_playlist = meta.get("is_playlist", False)
        count = meta.get("count", 0)
        qualities = meta.get("qualities", [])
        thumb_bytes = meta.get("thumbnail_bytes")

        self.title_label.setText(title)
        if is_playlist:
            self.channel_duration_label.setText(f"👤 Chaîne : {uploader}  |  📁 Playlist ({count} vidéos)")
            self.status_badge_label.setText("✅ Playlist détectée")
        else:
            self.channel_duration_label.setText(f"👤 Chaîne : {uploader}  |  ⏱️ Durée : {duration_str}")
            self.status_badge_label.setText("✅ Prêt à télécharger")

        if thumb_bytes:
            image = QImage.fromData(thumb_bytes)
            if not image.isNull():
                pixmap = QPixmap.fromImage(image).scaled(
                    140, 80, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
                )
                self.thumbnail_label.setPixmap(pixmap)
                self.thumbnail_label.setText("")
        else:
            self.thumbnail_label.setText("Miniature\nindisponible")

        if qualities:
            self.update_qualities(qualities)

        if meta.get("force_msg"):
            names = meta.get("available_names", [])
            msg = f"📌 {title}\n👤 {uploader} | ⏱️ {duration_str}"
            if names:
                msg += f"\n✅ Qualités : " + ", ".join(names[:6])
            self.communicate.update_signal.emit(msg)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier de destination", self.download_path)
        if folder:
            self.download_path = folder
            self.destination_label.setText(f"Dossier: {folder}")
            self.settings.setValue("download_path", folder)

    def open_folder(self):
        if not self.download_path or not os.path.exists(self.download_path):
            QMessageBox.warning(self, "Erreur", "Veuillez d'abord choisir un dossier valide.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.download_path))

    def open_last_downloaded_file(self):
        if self.last_downloaded_file and os.path.exists(self.last_downloaded_file):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_downloaded_file))
        elif self.download_path and os.path.exists(self.download_path):
            self.open_folder()
        else:
            QMessageBox.information(self, "Info", "Aucun fichier récent à ouvrir.")

    def on_download_finished_file(self, filepath):
        if filepath and os.path.exists(filepath):
            self.last_downloaded_file = filepath
            self.play_btn.setEnabled(True)
            self.play_btn.setText(f"▶️ Lire ({os.path.basename(filepath)[:18]}...)")

    def set_ui_downloading(self, is_downloading: bool):
        self.downloading = is_downloading
        self.url_input.setEnabled(not is_downloading)
        self.paste_btn.setEnabled(not is_downloading)
        self.select_folder_btn.setEnabled(not is_downloading)
        self.check_playlist_btn.setEnabled(not is_downloading)
        self.check_chapters_btn.setEnabled(not is_downloading)
        self.check_qualities_btn.setEnabled(not is_downloading)
        self.video_card.setEnabled(not is_downloading)
        self.audio_card.setEnabled(not is_downloading)
        self.video_radio.setEnabled(not is_downloading)
        self.audio_radio.setEnabled(not is_downloading)
        self.embed_metadata_checkbox.setEnabled(not is_downloading)
        self.playlist_range_input.setEnabled(not is_downloading)
        self.download_btn.setEnabled(not is_downloading)
        self.cancel_btn.setEnabled(is_downloading)

        if not is_downloading:
            self.set_active_mode_highlight(self.video_radio.isChecked())

    def update_qualities(self, qualities_list):
        current = self.quality_select.currentText()
        self.quality_select.clear()
        self.quality_select.addItems(qualities_list)
        index = self.quality_select.findText(current)
        if index >= 0:
            self.quality_select.setCurrentIndex(index)

    def check_yt_dlp(self) -> bool:
        try:
            subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            QMessageBox.critical(
                self, "Erreur Système",
                "yt-dlp est introuvable sur votre système.\n"
                "Veuillez l'installer et l'ajouter au PATH."
            )
            return False

    def check_playlist(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer une URL valide.")
            return

        if not self.check_yt_dlp():
            return

        self.communicate.update_signal.emit("⏳ Vérification de la playlist en cours...")
        thread = threading.Thread(target=self.fetch_playlist_info, args=(url,), daemon=True)
        thread.start()

    def fetch_playlist_info(self, url):
        cmd = get_base_yt_dlp_cmd() + ["--flat-playlist", "--dump-single-json", url]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            _type = data.get("_type")
            entries = data.get("entries")

            if _type in ("playlist", "multi_video") or isinstance(entries, list):
                title = data.get("title", "Sans titre")
                count = len(entries) if entries is not None else data.get("playlist_count", 0)
                msg = f"✅ Ce lien est une playlist.\n📌 Titre : {title}"
                if count:
                    msg += f"\n🔢 Nombre d'éléments : {count}"
                self.communicate.update_signal.emit(msg)
            else:
                title = data.get("title", "Sans titre")
                self.communicate.update_signal.emit(
                    f"ℹ️ Ce lien n'est pas une playlist (vidéo individuelle).\n📌 Titre : {title}"
                )
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            self.communicate.update_signal.emit("❌ Erreur: Impossible de vérifier la playlist.")

    def parse_available_qualities(self, data):
        formats = data.get("formats", [])
        audio_formats = [f for f in formats if f.get("vcodec") == "none" and (f.get("filesize") or f.get("filesize_approx"))]
        best_audio_size = max([(f.get("filesize") or f.get("filesize_approx")) for f in audio_formats], default=0)

        heights = sorted(list(set(f.get("height") for f in formats if f.get("height") and f.get("height") >= 144)), reverse=True)

        height_labels = {
            2160: "4K (2160p)",
            1440: "2K (1440p)",
            1080: "1080p",
            720: "720p",
            480: "480p",
            360: "360p",
            240: "240p",
            144: "144p",
        }

        max_size_str = ""
        if heights:
            max_h = heights[0]
            v_formats = [f for f in formats if f.get("height") == max_h and f.get("vcodec") != "none"]
            best_v_size = max([(f.get("filesize") or f.get("filesize_approx") or 0) for f in v_formats], default=0)
            if best_v_size > 0:
                max_size_str = format_bytes_human(best_v_size + best_audio_size)

        qualities = [f"Meilleure qualité{max_size_str}"]
        available_names = []
        for h in heights:
            label = height_labels.get(h, f"{h}p")
            v_formats = [f for f in formats if f.get("height") == h and f.get("vcodec") != "none"]
            best_v_size = max([(f.get("filesize") or f.get("filesize_approx") or 0) for f in v_formats], default=0)
            size_str = format_bytes_human(best_v_size + best_audio_size) if best_v_size > 0 else ""

            full_name = f"{label}{size_str}"
            if full_name not in qualities:
                qualities.append(full_name)
                available_names.append(full_name)

        return qualities, available_names

    def check_chapters(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer une URL valide.")
            return

        if not self.check_yt_dlp():
            return

        self.communicate.update_signal.emit("⏳ Vérification des chapitres en cours...")
        thread = threading.Thread(target=self.fetch_chapters_info, args=(url,), daemon=True)
        thread.start()

    def fetch_chapters_info(self, url):
        cmd = get_base_yt_dlp_cmd() + ["--no-playlist", "--dump-json", url]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)

            qualities, _ = self.parse_available_qualities(data)
            self.communicate.qualities_signal.emit(qualities)

            chapters = data.get("chapters", [])
            if chapters:
                message = "✅ Chapitres disponibles :\n"
                total_duration = data.get("duration") or (chapters[-1].get("end_time", chapters[-1].get("start_time", 0)) if chapters else 0)

                for i, chapter in enumerate(chapters, start=1):
                    start_time = chapter.get("start_time", 0)
                    title = chapter.get("title", "Sans titre")

                    formatted_start_time = format_duration(start_time)
                    if "end_time" in chapter:
                        end_time = chapter["end_time"]
                    elif i < len(chapters):
                        end_time = chapters[i].get("start_time", start_time)
                    else:
                        end_time = total_duration

                    duration = max(0, end_time - start_time)
                    formatted_duration = format_duration(duration)
                    message += f"{i:02d}. {title} ({formatted_start_time} - {formatted_duration})\n"

                message += f"\n⏳ Durée totale : {format_duration(total_duration)}"
                self.communicate.update_signal.emit(message)
            else:
                self.communicate.update_signal.emit("ℹ️ Aucun chapitre détecté pour cette vidéo.")
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            self.communicate.update_signal.emit("❌ Erreur: Impossible de récupérer les chapitres.")

    def start_download(self):
        if self.downloading:
            QMessageBox.warning(self, "Attention", "Téléchargement déjà en cours!")
            return

        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer une URL valide.")
            return

        if not self.download_path or not os.path.exists(self.download_path):
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un dossier de destination valide.")
            return

        if not self.check_yt_dlp():
            return

        self.download_info.clear()
        self.progress_bar.setValue(0)
        self.file_info_label.setText("")
        self.play_btn.setEnabled(False)
        self.play_btn.setText("▶️ Lire le fichier")
        self.communicate.update_signal.emit("🚀 Initialisation du téléchargement...")

        self.communicate.download_state_signal.emit(True)

        thread = threading.Thread(target=self.download, args=(url,), daemon=True)
        thread.start()

    def download(self, url):
        is_audio = self.audio_radio.isChecked()
        quality = self.quality_select.currentText()
        split_chapters = self.split_chapters_checkbox.isChecked()
        embed_meta = self.embed_metadata_checkbox.isChecked()
        download_subs = self.subtitles_checkbox.isChecked()
        playlist_range = self.playlist_range_input.text().strip()

        target_height = None
        if not is_audio and "Meilleure" not in quality:
            match = re.search(r'(\d+)p', quality)
            if match:
                target_height = int(match.group(1))

        progress_template = "KPARSER|%(progress.status)s|%(progress._percent_str)s|%(progress._downloaded_bytes_str)s|%(progress._total_bytes_str)s|%(progress._speed_str)s|%(progress._eta_str)s|%(progress.filename)s"

        cmd = get_base_yt_dlp_cmd() + [
            "--newline",
            "--progress",
            "--progress-template", progress_template,
            "--paths", self.download_path,
            "--retries", "10",
            "--fragment-retries", "10",
        ]

        # Métadonnées & Pochette
        if embed_meta:
            cmd += ["--embed-metadata", "--embed-thumbnail"]

        # Sous-titres
        if download_subs and not is_audio:
            cmd += [
                "--write-subs", "--write-auto-subs",
                "--sub-langs", "fr.*,en.*,-live_chat",
                "--embed-subs"
            ]

        # Plage playlist
        if playlist_range:
            cmd += ["--playlist-items", playlist_range]

        if split_chapters:
            parsed = urlparse(url)
            q = parse_qs(parsed.query)
            if "list" in q:
                del q["list"]
                new_query = urlencode(q, doseq=True)
                url = urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                                 parsed.params, new_query, parsed.fragment))
            cmd += [
                "--no-playlist",
                "--split-chapters",
                "-o", "%(title)s.%(ext)s",
                "-o", "chapter:%(title)s/%(chapter_number)03d - %(chapter)s.%(ext)s"
            ]
        else:
            cmd += ["-o", "%(title)s.%(ext)s"]

        if is_audio:
            audio_format = self.audio_format_select.currentText().lower()
            audio_quality_str = self.audio_bitrate_select.currentText()
            
            cmd += ["-x", "--audio-format", audio_format]
            if "320" in audio_quality_str:
                cmd += ["--audio-quality", "320K"]
            elif "256" in audio_quality_str:
                cmd += ["--audio-quality", "256K"]
            elif "192" in audio_quality_str:
                cmd += ["--audio-quality", "192K"]
            elif "128" in audio_quality_str:
                cmd += ["--audio-quality", "128K"]
            else:
                cmd += ["--audio-quality", "0"]
        else:
            if target_height is not None:
                cmd += ["-f", f"bestvideo[height<={target_height}]+bestaudio/best"]
            else:
                cmd += ["-f", "bestvideo+bestaudio/best"]

        cmd.append(url)

        detected_filepath = None
        try:
            self.download_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding='utf-8', errors='replace'
            )

            while True:
                line = self.download_process.stdout.readline()
                if not line and self.download_process.poll() is not None:
                    break
                if line:
                    stripped = line.strip()
                    file_from_line = self.parse_output(stripped)
                    if file_from_line:
                        detected_filepath = file_from_line

            self.download_process.wait()
            if self.download_process.returncode == 0:
                self.communicate.update_signal.emit("✅ Téléchargement terminé avec succès!")
                self.communicate.progress_signal.emit(100)
                
                # Trouver le fichier créé si non capturé directement
                if not detected_filepath or not os.path.exists(detected_filepath):
                    detected_filepath = self.find_latest_file_in_dir(self.download_path)

                if detected_filepath:
                    self.communicate.finished_file_signal.emit(detected_filepath)
                    # Enregistrer dans l'historique
                    history_item = {
                        "title": self.title_label.text() if self.title_label.text() != "Titre de la vidéo : En attente d'un lien..." else os.path.basename(detected_filepath),
                        "filepath": detected_filepath,
                        "date": time.strftime("%d/%m/%Y %H:%M"),
                        "type": "Audio" if is_audio else "Vidéo",
                        "size": format_bytes_human(os.path.getsize(detected_filepath)) if os.path.exists(detected_filepath) else ""
                    }
                    self.save_history_item(history_item)

            else:
                if self.downloading:
                    self.communicate.update_signal.emit("❌ Erreur lors du téléchargement.")
        except Exception as e:
            self.communicate.update_signal.emit(f"❌ Erreur: {str(e)}")
        finally:
            self.download_process = None
            self.communicate.download_state_signal.emit(False)

    def find_latest_file_in_dir(self, directory):
        try:
            files = [
                os.path.join(directory, f) for f in os.listdir(directory)
                if os.path.isfile(os.path.join(directory, f))
            ]
            if files:
                files.sort(key=os.path.getmtime, reverse=True)
                return files[0]
        except Exception:
            pass
        return None

    def cancel_download(self):
        if self.downloading:
            self.communicate.update_signal.emit("Annulation du téléchargement en cours...")

            if self.download_process is not None:
                try:
                    pid = self.download_process.pid
                    if pid and psutil.pid_exists(pid):
                        parent = psutil.Process(pid)
                        children = parent.children(recursive=True)
                        for child in children:
                            try:
                                child.terminate()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                        gone, still_alive = psutil.wait_procs(children, timeout=2)
                        for child in still_alive:
                            try:
                                child.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                        parent.terminate()
                        parent.wait(timeout=2)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                except Exception as e:
                    pass

            self.communicate.download_state_signal.emit(False)
            self.progress_bar.setValue(0)
            self.file_info_label.setText("")
            self.communicate.update_signal.emit("❌ Téléchargement annulé.")

    def parse_output(self, line: str):
        detected_file = None
        if line.startswith("KPARSER|"):
            parts = line.split("|")
            if len(parts) >= 7:
                status, percent_str, downloaded_str, total_str, speed_str, eta_str = parts[1:7]
                
                clean_percent = re.sub(r"[^\d.]", "", percent_str)
                if clean_percent:
                    try:
                        val = float(clean_percent)
                        self.communicate.progress_signal.emit(int(val))
                    except ValueError:
                        pass
                
                info = f"{downloaded_str.strip()} / {total_str.strip()}  |  Vitesse: {speed_str.strip()}  |  ETA: {eta_str.strip()}"
                self.communicate.file_info_signal.emit(info)

                if len(parts) >= 8 and parts[7].strip():
                    detected_file = parts[7].strip()
            return detected_file

        # Détection du nom de fichier dans les sorties yt-dlp usuelles
        if "[download] Destination:" in line:
            detected_file = line.replace("[download] Destination:", "").strip()
        elif "[Merger] Merging formats into" in line:
            m = re.search(r'Merging formats into "([^"]+)"', line)
            if m:
                detected_file = m.group(1)
        elif "[ExtractAudio] Destination:" in line:
            detected_file = line.replace("[ExtractAudio] Destination:", "").strip()

        if (
            "ERROR:" in line
            or "WARNING:" in line
            or "[download]" in line
            or "[ExtractAudio]" in line
            or "[Merger]" in line
            or "[info]" in line
        ):
            self.communicate.update_signal.emit(line)

        return detected_file

    def update_output(self, message):
        self.download_info.append(message)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_file_info(self, info):
        self.file_info_label.setText(info)

    # --- Historique UI ---
    def add_history_item_to_ui(self, item, prepend=False):
        title = item.get("title", "Fichier")
        date_str = item.get("date", "")
        f_type = item.get("type", "")
        size = item.get("size", "")
        filepath = item.get("filepath", "")

        display_text = f"[{f_type}] {title}\n📅 {date_str} {size}  |  📂 {filepath}"
        list_item = QListWidgetItem(display_text)
        list_item.setData(Qt.ItemDataRole.UserRole, filepath)

        if prepend:
            self.history_list.insertItem(0, list_item)
        else:
            self.history_list.addItem(list_item)

    def on_history_item_double_clicked(self, list_item):
        filepath = list_item.data(Qt.ItemDataRole.UserRole)
        if filepath and os.path.exists(filepath):
            QDesktopServices.openUrl(QUrl.fromLocalFile(filepath))
        else:
            QMessageBox.warning(self, "Fichier introuvable", f"Le fichier suivant n'existe plus :\n{filepath}")

    def open_selected_history_file(self):
        current = self.history_list.currentItem()
        if current:
            self.on_history_item_double_clicked(current)
        else:
            QMessageBox.information(self, "Info", "Veuillez sélectionner un élément dans l'historique.")

    def open_selected_history_folder(self):
        current = self.history_list.currentItem()
        if current:
            filepath = current.data(Qt.ItemDataRole.UserRole)
            if filepath and os.path.exists(filepath):
                folder = os.path.dirname(filepath)
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
            elif self.download_path and os.path.exists(self.download_path):
                self.open_folder()
        else:
            QMessageBox.information(self, "Info", "Veuillez sélectionner un élément dans l'historique.")

    def clear_history(self):
        reply = QMessageBox.question(
            self, "Confirmation",
            "Voulez-vous vraiment effacer tout l'historique ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history_list.clear()
            self.settings.setValue("download_history", "[]")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)
    ex = KDownloader()
    ex.show()
    sys.exit(app.exec())