import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QLineEdit, QApplication
)
from PyQt6.QtCore import Qt, QUrl, QSize, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from app.ui.icons import get_svg_icon
from app.config import AppConfig


class HistoryView(QWidget):
    history_cleared = pyqtSignal()

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header toolbar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        title_layout = QVBoxLayout()
        title_label = QLabel("Historique des Téléchargements", self)
        title_label.setStyleSheet("font-size: 13pt; font-weight: 700; color: #ffffff;")
        subtitle_label = QLabel("Retrouvez et ouvrez rapidement vos fichiers téléchargés", self)
        subtitle_label.setStyleSheet("font-size: 8.5pt; color: #64748b;")
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        self.btn_clear = QPushButton("Effacer l'historique", self)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setIcon(get_svg_icon("trash", normal_color="#f43f5e", size=14))
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #20171e;
                border: 1px solid #3d1c25;
                color: #f43f5e;
                font-size: 9pt;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #f43f5e;
                color: #ffffff;
            }
        """)
        self.btn_clear.clicked.connect(self.clear_history)
        header_layout.addWidget(self.btn_clear)

        layout.addLayout(header_layout)

        # Search / Filter Bar
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Rechercher dans l'historique...")
        self.search_bar.textChanged.connect(self.filter_history)
        layout.addWidget(self.search_bar)

        # History List Widget
        self.list_widget = QListWidget(self)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget, 1)

        # Bottom Actions Toolbar
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.btn_open_file = QPushButton("Ouvrir le fichier", self)
        self.btn_open_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_file.setIcon(get_svg_icon("play", normal_color="#f1f5f9", size=14))
        self.btn_open_file.clicked.connect(self.open_selected_file)
        actions_layout.addWidget(self.btn_open_file)

        self.btn_open_folder = QPushButton("Ouvrir dans l'explorateur", self)
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.setIcon(get_svg_icon("folder_open", normal_color="#f1f5f9", size=14))
        self.btn_open_folder.clicked.connect(self.open_selected_folder)
        actions_layout.addWidget(self.btn_open_folder)

        self.btn_copy_path = QPushButton("Copier le chemin", self)
        self.btn_copy_path.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_path.setIcon(get_svg_icon("paste", normal_color="#f1f5f9", size=14))
        self.btn_copy_path.clicked.connect(self.copy_selected_path)
        actions_layout.addWidget(self.btn_copy_path)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        self.load_history()

    def load_history(self):
        items = self.config.get_history()
        self.list_widget.clear()
        for item in items:
            self.add_item_to_list(item)

    def add_item_to_list(self, item: dict, prepend: bool = False):
        title = item.get("title", "Fichier")
        date_str = item.get("date", "")
        f_type = item.get("type", "Vidéo")
        size = item.get("size", "")
        filepath = item.get("filepath", "")

        icon_name = "music" if f_type == "Audio" else "video"
        icon = get_svg_icon(icon_name, normal_color="#6366f1", size=18)

        display_text = f"[{f_type}]  {title}\nDate: {date_str}   Taille: {size}\nChemin: {filepath}"
        list_item = QListWidgetItem(icon, display_text)
        list_item.setData(Qt.ItemDataRole.UserRole, filepath)
        list_item.setSizeHint(QSize(0, 68))

        if prepend:
            self.list_widget.insertItem(0, list_item)
        else:
            self.list_widget.addItem(list_item)

    def filter_history(self, text: str):
        query = text.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            match = query in item.text().lower()
            item.setHidden(not match)

    def on_item_double_clicked(self, item: QListWidgetItem):
        filepath = item.data(Qt.ItemDataRole.UserRole)
        if filepath and os.path.exists(filepath):
            QDesktopServices.openUrl(QUrl.fromLocalFile(filepath))
        else:
            QMessageBox.warning(self, "Fichier introuvable", f"Le fichier suivant n'existe plus :\n{filepath}")

    def open_selected_file(self):
        current = self.list_widget.currentItem()
        if current:
            self.on_item_double_clicked(current)
        else:
            QMessageBox.information(self, "Sélection", "Veuillez sélectionner un élément dans l'historique.")

    def open_selected_folder(self):
        current = self.list_widget.currentItem()
        if current:
            filepath = current.data(Qt.ItemDataRole.UserRole)
            if filepath and os.path.exists(filepath):
                folder = os.path.dirname(filepath)
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
            elif self.config.download_path and os.path.exists(self.config.download_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(self.config.download_path))
        else:
            QMessageBox.information(self, "Sélection", "Veuillez sélectionner un élément dans l'historique.")

    def copy_selected_path(self):
        current = self.list_widget.currentItem()
        if current:
            filepath = current.data(Qt.ItemDataRole.UserRole)
            if filepath:
                QApplication.clipboard().setText(filepath)
                QMessageBox.information(self, "Copié", "Chemin d'accès copié dans le presse-papier.")
        else:
            QMessageBox.information(self, "Sélection", "Veuillez sélectionner un élément dans l'historique.")

    def clear_history(self):
        reply = QMessageBox.question(
            self, "Confirmation",
            "Voulez-vous vraiment effacer tout l'historique des téléchargements ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config.clear_history()
            self.list_widget.clear()
            self.history_cleared.emit()
