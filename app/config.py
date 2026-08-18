import os
import json
from PyQt6.QtCore import QSettings, QStandardPaths


class AppConfig:
    """Manages application settings and history storage via QSettings."""

    def __init__(self):
        self.settings = QSettings("KDownloader", "App")

    @property
    def download_path(self) -> str:
        saved = self.settings.value("download_path", "")
        if saved and os.path.exists(saved):
            return saved
        
        default_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        if not default_path or not os.path.exists(default_path):
            default_path = os.path.expanduser("~/Downloads")
        
        self.download_path = default_path
        return default_path

    @download_path.setter
    def download_path(self, path: str):
        self.settings.setValue("download_path", path)

    @property
    def auto_fetch_metadata(self) -> bool:
        return self.settings.value("auto_fetch_metadata", True, type=bool)

    @auto_fetch_metadata.setter
    def auto_fetch_metadata(self, val: bool):
        self.settings.setValue("auto_fetch_metadata", val)

    @property
    def default_format(self) -> str:
        return self.settings.value("default_format", "video", type=str)

    @default_format.setter
    def default_format(self, val: str):
        self.settings.setValue("default_format", val)

    # --- History Management ---
    def get_history(self) -> list[dict]:
        raw = self.settings.value("download_history", "[]")
        try:
            return json.loads(raw)
        except Exception:
            return []

    def add_history_item(self, item: dict) -> list[dict]:
        history = self.get_history()
        history.insert(0, item)
        # Limit history to 150 items
        if len(history) > 150:
            history = history[:150]
        self.settings.setValue("download_history", json.dumps(history))
        return history

    def clear_history(self):
        self.settings.setValue("download_history", "[]")
