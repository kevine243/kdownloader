from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox,
    QLineEdit, QPushButton, QButtonGroup
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from app.ui.icons import get_svg_icon
from app.ui.theme import get_card_style


class SegmentedButton(QPushButton):
    def __init__(self, text: str, icon_name: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(get_svg_icon(icon_name, normal_color="#94a3b8", active_color="#ffffff", size=16))
        self.setIconSize(QSize(16, 16))
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                color: #94a3b8;
                font-weight: 600;
                font-size: 9.5pt;
            }
            QPushButton:hover {
                color: #f1f5f9;
                background-color: #1a1e2b;
            }
            QPushButton:checked {
                background-color: #6366f1;
                color: #ffffff;
            }
        """)


class FormatSelector(QFrame):
    mode_changed = pyqtSignal(bool)  # True = Video, False = Audio
    inspect_playlist_requested = pyqtSignal()
    inspect_chapters_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("format_selector")
        self.setStyleSheet(get_card_style(is_active=False))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # Header with Segmented Mode Switcher
        header_layout = QHBoxLayout()
        title_label = QLabel("Format de Téléchargement", self)
        title_label.setStyleSheet("font-weight: 700; font-size: 10pt; color: #f1f5f9;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Segmented Control Container
        seg_container = QFrame(self)
        seg_container.setStyleSheet("""
            QFrame {
                background-color: #0d0f15;
                border: 1px solid #1f2330;
                border-radius: 8px;
                padding: 2px;
            }
        """)
        seg_layout = QHBoxLayout(seg_container)
        seg_layout.setContentsMargins(2, 2, 2, 2)
        seg_layout.setSpacing(4)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.btn_video = SegmentedButton("Vidéo", "video", seg_container)
        self.btn_audio = SegmentedButton("Audio", "music", seg_container)

        self.btn_group.addButton(self.btn_video, 0)
        self.btn_group.addButton(self.btn_audio, 1)
        self.btn_video.setChecked(True)

        self.btn_video.toggled.connect(self._on_mode_toggled)

        seg_layout.addWidget(self.btn_video)
        seg_layout.addWidget(self.btn_audio)
        header_layout.addWidget(seg_container)

        main_layout.addLayout(header_layout)

        # Video Options Container
        self.video_container = QFrame(self)
        video_layout = QVBoxLayout(self.video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(8)

        v_row1 = QHBoxLayout()
        v_quality_lbl = QLabel("Résolution vidéo :", self)
        v_quality_lbl.setStyleSheet("color: #94a3b8; font-size: 9.5pt;")
        self.quality_select = QComboBox(self)
        self.quality_select.addItems([
            "Meilleure qualité", "4K (2160p)", "2K (1440p)",
            "1080p", "720p", "480p", "360p"
        ])
        v_row1.addWidget(v_quality_lbl)
        v_row1.addWidget(self.quality_select, 1)
        video_layout.addLayout(v_row1)

        v_checks_layout = QHBoxLayout()
        self.subtitles_checkbox = QCheckBox("Sous-titres intégrés (FR/EN)", self)
        self.split_chapters_checkbox = QCheckBox("Découper en chapitres", self)
        v_checks_layout.addWidget(self.subtitles_checkbox)
        v_checks_layout.addWidget(self.split_chapters_checkbox)
        v_checks_layout.addStretch()
        video_layout.addLayout(v_checks_layout)

        main_layout.addWidget(self.video_container)

        # Audio Options Container
        self.audio_container = QFrame(self)
        audio_layout = QVBoxLayout(self.audio_container)
        audio_layout.setContentsMargins(0, 0, 0, 0)
        audio_layout.setSpacing(8)

        a_row1 = QHBoxLayout()
        a_fmt_lbl = QLabel("Format de sortie :", self)
        a_fmt_lbl.setStyleSheet("color: #94a3b8; font-size: 9.5pt;")
        self.audio_format_select = QComboBox(self)
        self.audio_format_select.addItems(["MP3", "M4A", "FLAC", "WAV", "OPUS"])
        a_row1.addWidget(a_fmt_lbl)
        a_row1.addWidget(self.audio_format_select, 1)

        a_bitrate_lbl = QLabel("Débit / Qualité :", self)
        a_bitrate_lbl.setStyleSheet("color: #94a3b8; font-size: 9.5pt;")
        self.audio_bitrate_select = QComboBox(self)
        self.audio_bitrate_select.addItems([
            "Meilleure qualité (V0 / ~320k)",
            "320 kbps (CBR)",
            "256 kbps",
            "192 kbps (Standard)",
            "128 kbps (Éco)"
        ])
        a_row1.addWidget(a_bitrate_lbl)
        a_row1.addWidget(self.audio_bitrate_select, 1)
        audio_layout.addLayout(a_row1)

        a_checks_layout = QHBoxLayout()
        self.embed_metadata_checkbox = QCheckBox("Pochette d'album & Métadonnées ID3", self)
        self.embed_metadata_checkbox.setChecked(True)
        self.split_chapters_audio_checkbox = QCheckBox("Découper en chapitres (pistes)", self)
        a_checks_layout.addWidget(self.embed_metadata_checkbox)
        a_checks_layout.addWidget(self.split_chapters_audio_checkbox)
        a_checks_layout.addStretch()
        audio_layout.addLayout(a_checks_layout)

        # Synchronize split checkboxes between video and audio
        self.split_chapters_checkbox.toggled.connect(
            lambda checked: self.split_chapters_audio_checkbox.setChecked(checked)
            if self.split_chapters_audio_checkbox.isChecked() != checked else None
        )
        self.split_chapters_audio_checkbox.toggled.connect(
            lambda checked: self.split_chapters_checkbox.setChecked(checked)
            if self.split_chapters_checkbox.isChecked() != checked else None
        )

        main_layout.addWidget(self.audio_container)
        self.audio_container.hide()

        # Playlist range & tools section
        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(8)

        pl_label = QLabel("Plage playlist :", self)
        pl_label.setStyleSheet("color: #94a3b8; font-size: 9pt;")
        self.playlist_range_input = QLineEdit(self)
        self.playlist_range_input.setPlaceholderText("ex: 1-5, 8 ou laisser vide")
        self.playlist_range_input.setStyleSheet("padding: 6px 10px; font-size: 9pt;")

        tools_layout.addWidget(pl_label)
        tools_layout.addWidget(self.playlist_range_input, 1)

        self.btn_inspect_playlist = QPushButton("Vérifier Playlist", self)
        self.btn_inspect_playlist.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_inspect_playlist.setIcon(get_svg_icon("link", normal_color="#94a3b8", size=14))
        self.btn_inspect_playlist.setStyleSheet("padding: 6px 12px; font-size: 9pt;")
        self.btn_inspect_playlist.clicked.connect(self.inspect_playlist_requested.emit)

        self.btn_inspect_chapters = QPushButton("Chapitres", self)
        self.btn_inspect_chapters.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_inspect_chapters.setIcon(get_svg_icon("chapters", normal_color="#94a3b8", size=14))
        self.btn_inspect_chapters.setStyleSheet("padding: 6px 12px; font-size: 9pt;")
        self.btn_inspect_chapters.clicked.connect(self.inspect_chapters_requested.emit)

        tools_layout.addWidget(self.btn_inspect_playlist)
        tools_layout.addWidget(self.btn_inspect_chapters)
        main_layout.addLayout(tools_layout)

    def _on_mode_toggled(self, is_video: bool):
        self.video_container.setVisible(is_video)
        self.audio_container.setVisible(not is_video)
        self.mode_changed.emit(is_video)

    @property
    def is_video(self) -> bool:
        return self.btn_video.isChecked()

    def set_qualities(self, qualities: list[str]):
        current = self.quality_select.currentText()
        self.quality_select.clear()
        self.quality_select.addItems(qualities)
        idx = self.quality_select.findText(current)
        if idx >= 0:
            self.quality_select.setCurrentIndex(idx)

    def set_enabled(self, enabled: bool):
        self.btn_video.setEnabled(enabled)
        self.btn_audio.setEnabled(enabled)
        self.quality_select.setEnabled(enabled)
        self.subtitles_checkbox.setEnabled(enabled)
        self.split_chapters_checkbox.setEnabled(enabled)
        self.split_chapters_audio_checkbox.setEnabled(enabled)
        self.audio_format_select.setEnabled(enabled)
        self.audio_bitrate_select.setEnabled(enabled)
        self.embed_metadata_checkbox.setEnabled(enabled)
        self.playlist_range_input.setEnabled(enabled)
        self.btn_inspect_playlist.setEnabled(enabled)
        self.btn_inspect_chapters.setEnabled(enabled)
