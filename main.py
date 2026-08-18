import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt

from app.ui.main_window import MainWindow
from app.ui.theme import THEME_STYLESHEET
from app.ui.icons import get_svg_icon


def setup_app_icon(app: QApplication):
    # Try icon files if present, otherwise set vector logo
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "assets", "icon.png"),
        os.path.join(os.path.dirname(__file__), "icon.png"),
        os.path.join(os.path.dirname(__file__), "icon.ico"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            app.setWindowIcon(QIcon(path))
            return
    
    # Fallback to dynamic SVG logo icon
    app.setWindowIcon(get_svg_icon("logo", normal_color="#6366f1", size=64))


def main():
    # Windows High-DPI support
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("KDownloader")
    app.setOrganizationName("KDownloader")

    # Typography
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    # Stylesheet
    app.setStyleSheet(THEME_STYLESHEET)
    setup_app_icon(app)

    # Main Window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()