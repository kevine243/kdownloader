from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPainterPath
from app.ui.icons import get_svg_icon
from app.ui.theme import get_card_style


class MediaCard(QFrame):
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("media_card")
        self.setStyleSheet(get_card_style(is_active=False))

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(14)

        # 16:9 Thumbnail Image
        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setFixedSize(140, 80)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #0b0d13;
                border: 1px solid #1e2230;
                border-radius: 8px;
                color: #64748b;
                font-size: 8.5pt;
            }
        """)
        self.thumbnail_label.setText("Aucun aperçu")
        main_layout.addWidget(self.thumbnail_label)

        # Meta info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        self.title_label = QLabel("En attente d'un lien...", self)
        self.title_label.setStyleSheet("font-weight: 700; font-size: 10.5pt; color: #f8fafc;")
        self.title_label.setWordWrap(True)
        info_layout.addWidget(self.title_label)

        self.channel_duration_label = QLabel("Chaîne : —  •  Durée : —", self)
        self.channel_duration_label.setStyleSheet("color: #94a3b8; font-size: 9pt;")
        info_layout.addWidget(self.channel_duration_label)

        # Status badge line
        status_line = QHBoxLayout()
        status_line.setSpacing(8)

        self.status_badge = QLabel("Collez une URL pour commencer", self)
        self.status_badge.setStyleSheet("color: #6366f1; font-size: 8.5pt; font-weight: 500;")
        status_line.addWidget(self.status_badge)
        status_line.addStretch()

        self.refresh_btn = QPushButton("Actualiser", self)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setIcon(get_svg_icon("refresh", normal_color="#94a3b8", size=14))
        self.refresh_btn.setIconSize(QSize(14, 14))
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a1d28;
                border: 1px solid #272c3d;
                border-radius: 6px;
                padding: 4px 10px;
                color: #94a3b8;
                font-size: 8.5pt;
            }
            QPushButton:hover {
                background-color: #232838;
                color: #f8fafc;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        status_line.addWidget(self.refresh_btn)

        info_layout.addLayout(status_line)
        main_layout.addLayout(info_layout, 1)

    def set_loading(self, message: str = "Analyse des métadonnées en cours..."):
        self.status_badge.setText(f"⏳ {message}")
        self.status_badge.setStyleSheet("color: #f59e0b; font-size: 8.5pt;")

    def set_metadata(self, title: str, uploader: str, duration_str: str, is_playlist: bool, count: int, thumb_bytes: bytes | None):
        self.title_label.setText(title or "Sans titre")
        
        if is_playlist:
            self.channel_duration_label.setText(f"Chaîne : {uploader}  •  Playlist ({count} vidéos)")
            self.status_badge.setText("Playlist détectée")
            self.status_badge.setStyleSheet("color: #10b981; font-size: 8.5pt; font-weight: 600;")
        else:
            self.channel_duration_label.setText(f"Chaîne : {uploader}  •  Durée : {duration_str}")
            self.status_badge.setText("Prêt à télécharger")
            self.status_badge.setStyleSheet("color: #10b981; font-size: 8.5pt; font-weight: 600;")

        if thumb_bytes:
            image = QImage.fromData(thumb_bytes)
            if not image.isNull():
                pixmap = QPixmap.fromImage(image).scaled(
                    140, 80, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
                )
                rounded_pixmap = self._get_rounded_pixmap(pixmap, 8)
                self.thumbnail_label.setPixmap(rounded_pixmap)
                self.thumbnail_label.setText("")
                return
        
        self.thumbnail_label.setText("Miniature\nindisponible")

    def _get_rounded_pixmap(self, src: QPixmap, radius: int) -> QPixmap:
        dest = QPixmap(src.size())
        dest.fill(Qt.GlobalColor.transparent)
        painter = QPainter(dest)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, src.width(), src.height(), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, src)
        painter.end()
        return dest

    def reset_view(self):
        self.title_label.setText("En attente d'un lien...")
        self.channel_duration_label.setText("Chaîne : —  •  Durée : —")
        self.status_badge.setText("Collez une URL pour commencer")
        self.status_badge.setStyleSheet("color: #6366f1; font-size: 8.5pt;")
        self.thumbnail_label.clear()
        self.thumbnail_label.setText("Aucun aperçu")
