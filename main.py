import sys
import os
import re
import json
import shutil
import threading
import subprocess
import time
import psutil
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def get_ffmpeg_path():
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and os.path.exists(path):
            return path
    except Exception:
        pass
    return None


from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLineEdit, QPushButton, QLabel, QFileDialog, QRadioButton,
                             QComboBox, QCheckBox, QMessageBox, QTextEdit, QProgressBar,
                             QGroupBox)
from PyQt6.QtCore import pyqtSignal, QObject, QSettings, Qt
from PyQt6.QtGui import QIcon


class Communicate(QObject):
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    file_info_signal = pyqtSignal(str)
    download_state_signal = pyqtSignal(bool)


class KDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.communicate = Communicate()
        self.communicate.update_signal.connect(self.update_output)
        self.communicate.progress_signal.connect(self.update_progress)
        self.communicate.file_info_signal.connect(self.update_file_info)
        self.communicate.download_state_signal.connect(self.set_ui_downloading)

        self.downloading = False
        self.download_path = ""
        self.download_process = None

        self.settings = QSettings("KDownloader", "App")
        
        self.init_ui()
        self.load_settings()
        self.load_icon()

    def load_icon(self):
        # Chercher une icône dans le répertoire courant ou assets/
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
            self.destination_label.setText(f"Dossier: {self.download_path}")

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #45475a;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 14px;
                font-weight: bold;
                color: #89b4fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: #1e1e2e;
            }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                color: #cdd6f4;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 1px solid #89b4fa;
            }
            QPushButton {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px 14px;
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
            }
            QPushButton#cancel_btn:hover {
                background-color: #f5e0dc;
            }
            QPushButton#cancel_btn:disabled {
                background-color: #45475a;
                color: #7f849c;
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
            QRadioButton, QCheckBox {
                spacing: 8px;
                color: #cdd6f4;
            }
            QLabel {
                color: #cdd6f4;
            }
        """)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # --- Groupe 1: URL & Destination ---
        source_group = QGroupBox("Source & Destination")
        source_layout = QVBoxLayout()

        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Collez l'URL de la vidéo ou de la playlist ici...")
        source_layout.addWidget(self.url_input)

        folder_layout = QHBoxLayout()
        self.destination_label = QLabel("Dossier: Non sélectionné", self)
        self.destination_label.setWordWrap(True)
        folder_layout.addWidget(self.destination_label, 1)

        self.select_folder_btn = QPushButton("Choisir un dossier", self)
        self.select_folder_btn.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.select_folder_btn)

        source_layout.addLayout(folder_layout)
        source_group.setLayout(source_layout)
        main_layout.addWidget(source_group)

        # --- Groupe 2: Options de téléchargement ---
        options_group = QGroupBox("Options de téléchargement")
        options_layout = QGridLayout()

        # Format Radio
        format_layout = QHBoxLayout()
        self.video_radio = QRadioButton("Vidéo", self)
        self.audio_radio = QRadioButton("Audio (MP3)", self)
        self.video_radio.setChecked(True)
        format_layout.addWidget(self.video_radio)
        format_layout.addWidget(self.audio_radio)
        format_layout.addStretch()

        options_layout.addLayout(format_layout, 0, 0, 1, 2)

        # Qualité combo
        quality_label = QLabel("Qualité vidéo:", self)
        self.quality_select = QComboBox(self)
        self.quality_select.addItems([
            "Meilleure qualité", "4K", "2K", "1440p",
            "1080p", "720p", "480p", "360p"
        ])
        options_layout.addWidget(quality_label, 1, 0)
        options_layout.addWidget(self.quality_select, 1, 1)

        # Option de découpage
        self.split_chapters_checkbox = QCheckBox("Découper en chapitres", self)
        options_layout.addWidget(self.split_chapters_checkbox, 2, 0, 1, 2)

        # Boutons d'inspection (Playlist / Chapitres)
        inspect_layout = QHBoxLayout()
        self.check_playlist_btn = QPushButton("Vérifier la playlist", self)
        self.check_playlist_btn.clicked.connect(self.check_playlist)
        inspect_layout.addWidget(self.check_playlist_btn)

        self.check_chapters_btn = QPushButton("Vérifier les chapitres", self)
        self.check_chapters_btn.clicked.connect(self.check_chapters)
        inspect_layout.addWidget(self.check_chapters_btn)

        options_layout.addLayout(inspect_layout, 3, 0, 1, 2)

        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        # --- Groupe 3: Action, Logs & Progression ---
        status_group = QGroupBox("Progression & Journaux")
        status_layout = QVBoxLayout()

        action_layout = QHBoxLayout()
        self.download_btn = QPushButton("Télécharger", self)
        self.download_btn.setObjectName("download_btn")
        self.download_btn.clicked.connect(self.start_download)
        action_layout.addWidget(self.download_btn)

        self.cancel_btn = QPushButton("Annuler", self)
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_download)
        action_layout.addWidget(self.cancel_btn)

        status_layout.addLayout(action_layout)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar)

        self.file_info_label = QLabel("", self)
        self.file_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.file_info_label)

        self.download_info = QTextEdit(self)
        self.download_info.setReadOnly(True)
        status_layout.addWidget(self.download_info)

        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        self.setLayout(main_layout)
        self.setWindowTitle("KDownloader - yt-dlp GUI")
        self.resize(640, 720)
        self.apply_stylesheet()

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier de destination")
        if folder:
            self.download_path = folder
            self.destination_label.setText(f"Dossier: {folder}")
            self.settings.setValue("download_path", folder)

    def set_ui_downloading(self, is_downloading: bool):
        self.downloading = is_downloading
        self.url_input.setEnabled(not is_downloading)
        self.select_folder_btn.setEnabled(not is_downloading)
        self.check_playlist_btn.setEnabled(not is_downloading)
        self.check_chapters_btn.setEnabled(not is_downloading)
        self.video_radio.setEnabled(not is_downloading)
        self.audio_radio.setEnabled(not is_downloading)
        self.quality_select.setEnabled(not is_downloading)
        self.split_chapters_checkbox.setEnabled(not is_downloading)
        self.download_btn.setEnabled(not is_downloading)
        self.cancel_btn.setEnabled(is_downloading)

    def check_yt_dlp(self) -> bool:
        try:
            subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            QMessageBox.critical(
                self, "Erreur Systéme",
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
        cmd = ["yt-dlp", "--flat-playlist", "--dump-single-json", "--extractor-args", "youtube:player_client=android", url]
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
        cmd = ["yt-dlp", "--no-playlist", "--dump-json", "--extractor-args", "youtube:player_client=android", url]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            chapters = data.get("chapters", [])
            if chapters:
                message = "✅ Chapitres disponibles:\n"
                total_duration = data.get("duration") or (chapters[-1].get("end_time", chapters[-1].get("start_time", 0)) if chapters else 0)

                for i, chapter in enumerate(chapters, start=1):
                    start_time = chapter.get("start_time", 0)
                    title = chapter.get("title", "Sans titre")

                    start_minutes = int(start_time) // 60
                    start_seconds = int(start_time) % 60
                    formatted_start_time = f"{start_minutes:02d}:{start_seconds:02d}"

                    if "end_time" in chapter:
                        end_time = chapter["end_time"]
                    elif i < len(chapters):
                        end_time = chapters[i].get("start_time", start_time)
                    else:
                        end_time = total_duration

                    duration = max(0, end_time - start_time)
                    dur_minutes = int(duration) // 60
                    dur_seconds = int(duration) % 60
                    formatted_duration = f"{dur_minutes:02d}:{dur_seconds:02d}"

                    message += f"{i:03d} - {title} commence à {formatted_start_time} (durée: {formatted_duration})\n"

                total_minutes = int(total_duration) // 60
                total_seconds = int(total_duration) % 60
                formatted_total_duration = f"{total_minutes:02d}:{total_seconds:02d}"
                message += f"\n⏳ Durée totale de la vidéo : {formatted_total_duration}"

                self.communicate.update_signal.emit(message)
            else:
                self.communicate.update_signal.emit("ℹ️ Aucun chapitre détecté.")
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

        if not self.download_path:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un dossier de destination.")
            return

        if not self.check_yt_dlp():
            return

        self.download_info.clear()
        self.progress_bar.setValue(0)
        self.file_info_label.setText("")
        self.communicate.update_signal.emit("🚀 Initialisation du téléchargement...")

        self.communicate.download_state_signal.emit(True)

        thread = threading.Thread(target=self.download, args=(url,), daemon=True)
        thread.start()

    def download(self, url):
        is_audio = self.audio_radio.isChecked()
        quality = self.quality_select.currentText()
        split_chapters = self.split_chapters_checkbox.isChecked()

        quality_map = {
            "Meilleure qualité": None,
            "4K": 2160,
            "2K": 1440,
            "1440p": 1440,
            "1080p": 1080,
            "720p": 720,
            "480p": 480,
            "360p": 360,
        }

        progress_template = "KPARSER|%(progress.status)s|%(progress._percent_str)s|%(progress._downloaded_bytes_str)s|%(progress._total_bytes_str)s|%(progress._speed_str)s|%(progress._eta_str)s"

        cmd = [
            "yt-dlp",
            "--newline",
            "--progress",
            "--progress-template", progress_template,
            "--paths", self.download_path,
            "--extractor-args", "youtube:player_client=android",
        ]

        if shutil.which("node"):
            cmd += ["--js-runtimes", "node"]

        ffmpeg_path = get_ffmpeg_path()
        if ffmpeg_path:
            cmd += ["--ffmpeg-location", ffmpeg_path]

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
            cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
        else:
            if quality_map.get(quality) is not None:
                cmd += ["-f", f"bestvideo[height<={quality_map[quality]}]+bestaudio/best"]
            else:
                cmd += ["-f", "bestvideo+bestaudio/best"]

        cmd.append(url)

        try:
            self.download_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )

            while True:
                line = self.download_process.stdout.readline()
                if not line and self.download_process.poll() is not None:
                    break
                if line:
                    self.parse_output(line.strip())

            self.download_process.wait()
            if self.download_process.returncode == 0:
                self.communicate.update_signal.emit("✅ Téléchargement terminé avec succès!")
                self.communicate.progress_signal.emit(100)
            else:
                if self.downloading:
                    self.communicate.update_signal.emit("❌ Erreur lors du téléchargement.")
        except Exception as e:
            self.communicate.update_signal.emit(f"❌ Erreur: {str(e)}")
        finally:
            self.download_process = None
            self.communicate.download_state_signal.emit(False)

    def cancel_download(self):
        if self.downloading:
            self.communicate.update_signal.emit("Annulation du téléchargement en cours...")

            if self.download_process is not None:
                try:
                    parent = psutil.Process(self.download_process.pid)
                    for child in parent.children(recursive=True):
                        child.terminate()
                    gone, still_alive = psutil.wait_procs(parent.children(), timeout=3)
                    for child in still_alive:
                        child.kill()
                    self.download_process.terminate()
                    self.download_process.wait(timeout=3)
                except Exception as e:
                    print(f"Erreur lors de l'arrêt du processus: {e}")

            self.communicate.download_state_signal.emit(False)
            self.progress_bar.setValue(0)
            self.file_info_label.setText("")
            self.communicate.update_signal.emit("❌ Téléchargement annulé.")

    def parse_output(self, line: str):
        if line.startswith("KPARSER|"):
            parts = line.split("|")
            if len(parts) >= 7:
                status, percent_str, downloaded_str, total_str, speed_str, eta_str = parts[1:7]
                
                # Extraction du pourcentage pour la barre de progression
                clean_percent = re.sub(r"[^\d.]", "", percent_str)
                if clean_percent:
                    try:
                        val = float(clean_percent)
                        self.communicate.progress_signal.emit(int(val))
                    except ValueError:
                        pass
                
                # Formatage de l'info de fichier
                info = f"{downloaded_str.strip()} / {total_str.strip()}  |  Vitesse: {speed_str.strip()}  |  ETA: {eta_str.strip()}"
                self.communicate.file_info_signal.emit(info)
            return

        if (
            "ERROR:" in line
            or "WARNING:" in line
            or "[download]" in line
            or "[ExtractAudio]" in line
            or "[Merger]" in line
            or "[info]" in line
        ):
            self.communicate.update_signal.emit(line)

    def update_output(self, message):
        self.download_info.append(message)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_file_info(self, info):
        self.file_info_label.setText(info)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = KDownloader()
    ex.show()
    sys.exit(app.exec())