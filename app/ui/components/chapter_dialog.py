from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from app.core.utils import format_duration
from app.ui.icons import get_svg_icon


class ChapterDialog(QDialog):
    """
    Modal dialog displaying the list of chapters found in a media URL,
    with timestamps, durations, and split download action.
    """
    download_split_requested = pyqtSignal()

    def __init__(self, chapters: list[dict], title: str = "", total_duration: int = 0, parent=None):
        super().__init__(parent)
        self.chapters = chapters
        self.video_title = title or "Vidéo"
        self.total_duration = total_duration

        self.setWindowTitle("📑 Liste des Chapitres")
        self.setMinimumSize(680, 480)
        self.resize(720, 520)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1117;
                border: 1px solid #1e222e;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Section
        header_card = QFrame(self)
        header_card.setStyleSheet("""
            QFrame {
                background-color: #161922;
                border: 1px solid #282d3d;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        h_layout = QVBoxLayout(header_card)
        h_layout.setSpacing(6)

        t_lbl = QLabel(self.video_title, header_card)
        t_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        t_lbl.setStyleSheet("color: #f8fafc; border: none; background: transparent;")
        t_lbl.setWordWrap(True)

        info_text = f"📑 {len(self.chapters)} chapitres détectés"
        if self.total_duration > 0:
            info_text += f"  •  Durée totale : {format_duration(self.total_duration)}"
        
        info_lbl = QLabel(info_text, header_card)
        info_lbl.setStyleSheet("color: #94a3b8; font-size: 9.5pt; border: none; background: transparent;")

        h_layout.addWidget(t_lbl)
        h_layout.addWidget(info_lbl)
        layout.addWidget(header_card)

        # Chapters Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["N°", "Titre du Chapitre", "Début", "Durée"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #13151d;
                alternate-background-color: #171a24;
                border: 1px solid #262a38;
                border-radius: 8px;
                gridline-color: #1e222e;
                color: #e2e8f0;
                font-size: 9.5pt;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #1e222e;
            }
            QTableWidget::item:selected {
                background-color: #23293d;
                color: #60a5fa;
            }
            QHeaderView::section {
                background-color: #161924;
                color: #94a3b8;
                font-weight: bold;
                font-size: 9pt;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #2b3040;
            }
        """)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 50)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 90)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 90)

        self._populate_table()
        layout.addWidget(self.table, 1)

        # Bottom Actions Bar
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        note_lbl = QLabel("💡 Cocher 'Découper en chapitres' créera un fichier séparé par chapitre.", self)
        note_lbl.setStyleSheet("color: #64748b; font-size: 8.5pt;")
        actions_layout.addWidget(note_lbl, 1)

        self.btn_close = QPushButton("Fermer", self)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #1e222e;
                color: #cbd5e1;
                border: 1px solid #2d3345;
                border-radius: 8px;
                padding: 9px 18px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2b3040;
                color: #ffffff;
            }
        """)
        self.btn_close.clicked.connect(self.accept)

        self.btn_download_split = QPushButton("Découper & Télécharger", self)
        self.btn_download_split.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download_split.setIcon(get_svg_icon("download", normal_color="#ffffff", size=16))
        self.btn_download_split.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #4f46e5);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 9px 20px;
                font-weight: bold;
                font-size: 9.5pt;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #4338ca);
            }
        """)
        self.btn_download_split.clicked.connect(self._on_split_clicked)

        actions_layout.addWidget(self.btn_close)
        actions_layout.addWidget(self.btn_download_split)
        layout.addLayout(actions_layout)

    def _populate_table(self):
        self.table.setRowCount(len(self.chapters))
        for row, ch in enumerate(self.chapters):
            start = ch.get("start_time", 0)
            end = ch.get("end_time", 0)
            dur = max(0, int(end - start)) if end > start else 0

            # Item Index
            item_num = QTableWidgetItem(f"{row + 1:02d}")
            item_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Item Title
            item_title = QTableWidgetItem(ch.get("title", f"Chapitre {row + 1}"))

            # Item Start
            item_start = QTableWidgetItem(format_duration(int(start)))
            item_start.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Item Duration
            item_dur = QTableWidgetItem(format_duration(dur) if dur > 0 else "--:--")
            item_dur.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 0, item_num)
            self.table.setItem(row, 1, item_title)
            self.table.setItem(row, 2, item_start)
            self.table.setItem(row, 3, item_dur)

    def _on_split_clicked(self):
        self.download_split_requested.emit()
        self.accept()
