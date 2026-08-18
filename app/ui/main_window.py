import os
import time
import threading
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QMessageBox,
    QFileDialog, QApplication
)
from PyQt6.QtCore import pyqtSignal, QObject, Qt, QUrl
from PyQt6.QtGui import QKeySequence, QShortcut, QDesktopServices, QIcon

from app.config import AppConfig
from app.core.ytdlp import check_yt_dlp
from app.core.inspector import fetch_metadata, fetch_playlist_info, fetch_chapters_info, MediaMetadata
from app.core.downloader import DownloadProcess, DownloadOptions
from app.core.parser import ProgressData
from app.core.utils import format_duration, format_bytes_human
from app.ui.components.sidebar import Sidebar
from app.ui.components.chapter_dialog import ChapterDialog
from app.ui.views.download_view import DownloadView
from app.ui.views.history_view import HistoryView
from app.ui.views.log_view import LogView
from app.ui.views.settings_view import SettingsView


class Communicate(QObject):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(object)  # ProgressData
    download_state_signal = pyqtSignal(bool)
    finished_file_signal = pyqtSignal(str)
    metadata_signal = pyqtSignal(object)  # MediaMetadata
    qualities_signal = pyqtSignal(list)
    chapters_signal = pyqtSignal(list, str, int)  # chapters, title, total_duration


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.config = AppConfig()
        self.communicate = Communicate()

        self.current_download_process: DownloadProcess | None = None
        self.last_downloaded_file: str | None = None
        self.is_downloading = False

        self._setup_signals()
        self._init_ui()
        self._setup_shortcuts()

        # Drag & Drop support
        self.setAcceptDrops(True)

    def _setup_signals(self):
        self.communicate.log_signal.connect(self._on_log)
        self.communicate.progress_signal.connect(self._on_progress)
        self.communicate.download_state_signal.connect(self._on_download_state_changed)
        self.communicate.finished_file_signal.connect(self._on_download_finished)
        self.communicate.metadata_signal.connect(self._on_metadata_received)
        self.communicate.qualities_signal.connect(self._on_qualities_received)
        self.communicate.chapters_signal.connect(self._on_chapters_received)

    def _init_ui(self):
        self.setWindowTitle("KDownloader Pro")
        self.setMinimumSize(850, 620)
        self.resize(980, 720)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Navigation Sidebar
        self.sidebar = Sidebar(self)
        self.sidebar.page_changed.connect(self._on_page_changed)
        main_layout.addWidget(self.sidebar)

        # 2. View Stack
        self.stack = QStackedWidget(self)
        
        self.download_view = DownloadView(self.stack)
        self.history_view = HistoryView(self.config, self.stack)
        self.log_view = LogView(self.stack)
        self.settings_view = SettingsView(self.config, self.stack)

        self.stack.addWidget(self.download_view)  # 0
        self.stack.addWidget(self.history_view)   # 1
        self.stack.addWidget(self.log_view)       # 2
        self.stack.addWidget(self.settings_view)   # 3

        main_layout.addWidget(self.stack, 1)

        # Connect Download View Component signals
        self.download_view.url_bar.url_auto_detected.connect(self.auto_inspect_url)
        self.download_view.url_bar.url_submitted.connect(self.start_download)
        self.download_view.media_card.refresh_requested.connect(lambda: self.inspect_url(force_msg=True))

        self.download_view.format_selector.inspect_playlist_requested.connect(self.inspect_playlist)
        self.download_view.format_selector.inspect_chapters_requested.connect(self.inspect_chapters)

        panel = self.download_view.progress_panel
        panel.set_folder_text(self.config.download_path)
        panel.download_requested.connect(self.start_download)
        panel.cancel_requested.connect(self.cancel_download)
        panel.open_file_requested.connect(self.open_last_file)
        panel.change_folder_requested.connect(self.select_download_folder)
        panel.open_folder_requested.connect(self.open_download_folder)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self.start_download)
        QShortcut(QKeySequence("Ctrl+V"), self, activated=self.download_view.url_bar.paste_from_clipboard)
        QShortcut(QKeySequence("Escape"), self, activated=self.cancel_download)
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self.sidebar.set_current_page(0))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self.sidebar.set_current_page(1))
        QShortcut(QKeySequence("Ctrl+3"), self, activated=lambda: self.sidebar.set_current_page(2))
        QShortcut(QKeySequence("Ctrl+4"), self, activated=lambda: self.sidebar.set_current_page(3))

    def _on_page_changed(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == 1:
            self.history_view.load_history()
        elif index == 3:
            self.settings_view.folder_path_lbl.setText(self.config.download_path)

    # --- Drag and Drop ---
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
            text = event.mimeData().text().strip()

        if text.startswith("http://") or text.startswith("https://"):
            self.download_view.url_bar.setText(text)
            self.auto_inspect_url(text)
            self.sidebar.set_current_page(0)

    # --- Inspection & Metadata ---
    def auto_inspect_url(self, url: str):
        if not self.config.auto_fetch_metadata:
            return
        self.inspect_url(url=url, force_msg=False)

    def inspect_url(self, url: str | None = None, force_msg: bool = False):
        target_url = url or self.download_view.url_bar.text()
        if not target_url or not (target_url.startswith("http://") or target_url.startswith("https://")):
            if force_msg:
                QMessageBox.warning(self, "Erreur", "Veuillez entrer une URL valide.")
            return

        ok, err = check_yt_dlp()
        if not ok:
            QMessageBox.critical(self, "yt-dlp Introuvable", f"Erreur système :\n{err}")
            return

        self.download_view.media_card.set_loading("Analyse des métadonnées et miniature...")
        if force_msg:
            self.communicate.log_signal.emit(f"🔍 Analyse détaillée de {target_url}...")

        def _worker():
            try:
                meta = fetch_metadata(target_url)
                self.communicate.metadata_signal.emit(meta)
            except Exception as e:
                self.communicate.log_signal.emit(f"❌ Erreur lors de l'analyse : {str(e)}")

        threading.Thread(target=_worker, daemon=True).start()

    def _on_metadata_received(self, meta: MediaMetadata):
        self.download_view.media_card.set_metadata(
            title=meta.title,
            uploader=meta.uploader,
            duration_str=meta.duration_str,
            is_playlist=meta.is_playlist,
            count=meta.count,
            thumb_bytes=meta.thumbnail_bytes
        )
        if meta.qualities:
            self.download_view.format_selector.set_qualities(meta.qualities)

        self.communicate.log_signal.emit(
            f"📌 {meta.title}\n👤 {meta.uploader}  •  ⏱️ {meta.duration_str}\n"
            f"✅ Qualités disponibles : {', '.join(meta.available_names[:5]) if meta.available_names else 'Défaut'}"
        )

    def _on_qualities_received(self, qualities: list[str]):
        self.download_view.format_selector.set_qualities(qualities)

    def inspect_playlist(self):
        url = self.download_view.url_bar.text()
        if not url:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer une URL.")
            return

        self.communicate.log_signal.emit("⏳ Vérification de la playlist...")

        def _worker():
            try:
                is_pl, title, count = fetch_playlist_info(url)
                if is_pl:
                    self.communicate.log_signal.emit(f"✅ Playlist détectée : {title} ({count} éléments)")
                else:
                    self.communicate.log_signal.emit(f"ℹ️ Vidéo individuelle : {title}")
            except Exception as e:
                self.communicate.log_signal.emit(f"❌ Erreur playlist : {str(e)}")

        threading.Thread(target=_worker, daemon=True).start()

    def inspect_chapters(self):
        url = self.download_view.url_bar.text()
        if not url:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer une URL.")
            return

        self.communicate.log_signal.emit("⏳ Vérification des chapitres...")

        def _worker():
            try:
                chapters, qualities, total_duration = fetch_chapters_info(url)
                title = self.download_view.media_card.title_label.text()
                if qualities:
                    self.communicate.qualities_signal.emit(qualities)
                if chapters:
                    msg = f"✅ {len(chapters)} chapitres détectés :\n"
                    for i, ch in enumerate(chapters, 1):
                        start = format_duration(ch.get("start_time", 0))
                        msg += f"{i:02d}. {ch.get('title', 'Sans titre')} ({start})\n"
                    self.communicate.log_signal.emit(msg)
                else:
                    self.communicate.log_signal.emit("ℹ️ Aucun chapitre détecté.")
                self.communicate.chapters_signal.emit(chapters, title, total_duration)
            except Exception as e:
                self.communicate.log_signal.emit(f"❌ Erreur chapitres : {str(e)}")

        threading.Thread(target=_worker, daemon=True).start()

    def _on_chapters_received(self, chapters: list, title: str, total_duration: int):
        if not chapters:
            QMessageBox.information(self, "Chapitres", "Aucun chapitre n'a été détecté dans cette vidéo.")
            return
        
        dialog = ChapterDialog(chapters, title=title, total_duration=total_duration, parent=self)
        dialog.download_split_requested.connect(self._on_split_download_from_dialog)
        dialog.exec()

    def _on_split_download_from_dialog(self):
        self.download_view.format_selector.split_chapters_checkbox.setChecked(True)
        self.start_download()

    # --- Folder Actions ---
    def select_download_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Dossier de destination", self.config.download_path)
        if folder:
            self.config.download_path = folder
            self.download_view.progress_panel.set_folder_text(folder)
            self.settings_view.folder_path_lbl.setText(folder)

    def open_download_folder(self):
        path = self.config.download_path
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(self, "Erreur", "Le dossier n'existe pas.")

    def open_last_file(self):
        if self.last_downloaded_file and os.path.exists(self.last_downloaded_file):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_downloaded_file))
        else:
            self.open_download_folder()

    # --- Download Engine ---
    def start_download(self):
        if self.is_downloading:
            QMessageBox.warning(self, "Attention", "Un téléchargement est déjà en cours.")
            return

        url = self.download_view.url_bar.text()
        if not url:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer une URL valide.")
            return

        if not os.path.exists(self.config.download_path):
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un dossier de destination existant.")
            return

        fmt = self.download_view.format_selector
        is_audio = not fmt.is_video

        options = DownloadOptions(
            url=url,
            download_path=self.config.download_path,
            is_audio=is_audio,
            quality=fmt.quality_select.currentText(),
            audio_format=fmt.audio_format_select.currentText(),
            audio_bitrate=fmt.audio_bitrate_select.currentText(),
            embed_metadata=fmt.embed_metadata_checkbox.isChecked(),
            subtitles=fmt.subtitles_checkbox.isChecked(),
            split_chapters=fmt.split_chapters_checkbox.isChecked(),
            playlist_range=fmt.playlist_range_input.text().strip()
        )

        self.current_download_process = DownloadProcess(options)
        self.communicate.download_state_signal.emit(True)
        self.communicate.log_signal.emit(f"🚀 Démarrage du téléchargement : {url}")
        self.download_view.progress_panel.set_progress(0, "Démarrage du téléchargement...")

        def _download_thread():
            success = self.current_download_process.run(
                on_log=self.communicate.log_signal.emit,
                on_progress=self.communicate.progress_signal.emit,
                on_file_found=lambda f: None
            )
            if success:
                self.communicate.log_signal.emit("✅ Téléchargement terminé avec succès!")
                if self.current_download_process.detected_filepath:
                    self.communicate.finished_file_signal.emit(self.current_download_process.detected_filepath)
            else:
                if not self.current_download_process.cancelled:
                    self.communicate.log_signal.emit("❌ Le téléchargement a échoué.")
            
            self.communicate.download_state_signal.emit(False)

        threading.Thread(target=_download_thread, daemon=True).start()

    def cancel_download(self):
        if self.is_downloading and self.current_download_process:
            self.communicate.log_signal.emit("⏹️ Annulation du téléchargement...")
            self.current_download_process.cancel()
            self.communicate.download_state_signal.emit(False)
            self.download_view.progress_panel.set_progress(0, "Téléchargement annulé")

    def _on_download_state_changed(self, is_downloading: bool):
        self.is_downloading = is_downloading
        self.download_view.set_downloading_state(is_downloading)

    def _on_progress(self, progress: ProgressData):
        metrics = f"{progress.downloaded_str} / {progress.total_str}  •  {progress.speed_str}  •  ETA: {progress.eta_str}"
        self.download_view.progress_panel.set_progress(progress.percent, metrics)

    def _on_download_finished(self, filepath: str):
        self.last_downloaded_file = filepath
        self.download_view.progress_panel.set_progress(100, "Téléchargement terminé !")
        self.download_view.progress_panel.set_finished_file(os.path.basename(filepath))

        title = self.download_view.media_card.title_label.text()
        if title == "En attente d'un lien...":
            title = os.path.basename(filepath)

        f_type = "Audio" if not self.download_view.format_selector.is_video else "Vidéo"
        size = format_bytes_human(os.path.getsize(filepath)) if os.path.exists(filepath) else ""

        history_item = {
            "title": title,
            "filepath": filepath,
            "date": time.strftime("%d/%m/%Y %H:%M"),
            "type": f_type,
            "size": size
        }
        self.config.add_history_item(history_item)
        self.history_view.load_history()

    def _on_log(self, text: str):
        self.log_view.append_log(text)
