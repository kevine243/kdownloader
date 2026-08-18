"""
Modern Dark Theme System for KDownloader
"""

THEME_STYLESHEET = """
/* --- Global Window & Font Defaults --- */
QWidget {
    background-color: #0f1117;
    color: #f1f5f9;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 10pt;
    outline: none;
}

/* --- Scroll Areas & Bars --- */
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #2b3040;
    min-height: 30px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 6px;
}
QScrollBar::handle:horizontal {
    background: #2b3040;
    min-width: 30px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover {
    background: #475569;
}

/* --- Input Fields --- */
QLineEdit {
    background-color: #13151d;
    border: 1px solid #262a38;
    border-radius: 8px;
    padding: 10px 14px;
    color: #f8fafc;
    font-size: 10pt;
    selection-background-color: #6366f1;
}
QLineEdit:focus {
    border: 1px solid #6366f1;
    background-color: #161924;
}
QLineEdit:disabled {
    background-color: #0b0d13;
    border-color: #1e222e;
    color: #475569;
}

/* --- Combo Boxes --- */
QComboBox {
    background-color: #161922;
    border: 1px solid #282d3d;
    border-radius: 8px;
    padding: 7px 12px;
    color: #f1f5f9;
    font-weight: 500;
    min-height: 22px;
}
QComboBox:hover {
    border-color: #3b4259;
    background-color: #1b1f2b;
}
QComboBox:focus {
    border-color: #6366f1;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left-width: 0px;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}
QComboBox QAbstractItemView {
    background-color: #161924;
    border: 1px solid #282d3d;
    border-radius: 8px;
    padding: 4px;
    color: #f1f5f9;
    selection-background-color: #6366f1;
    selection-color: #ffffff;
}

/* --- Standard Push Buttons --- */
QPushButton {
    background-color: #1e2230;
    border: 1px solid #2d3345;
    border-radius: 8px;
    padding: 8px 16px;
    color: #f1f5f9;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #282d40;
    border-color: #3f4760;
}
QPushButton:pressed {
    background-color: #181b26;
}
QPushButton:disabled {
    background-color: #12141c;
    border-color: #1c202a;
    color: #475569;
}

/* --- Primary Accent Buttons --- */
QPushButton#primary_btn {
    background-color: #6366f1;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    color: #ffffff;
    font-weight: 700;
    font-size: 10.5pt;
}
QPushButton#primary_btn:hover {
    background-color: #4f46e5;
}
QPushButton#primary_btn:pressed {
    background-color: #4338ca;
}
QPushButton#primary_btn:disabled {
    background-color: #2d3148;
    color: #636882;
}

/* --- Danger / Cancel Buttons --- */
QPushButton#danger_btn {
    background-color: #271c24;
    border: 1px solid #4d1e28;
    border-radius: 8px;
    padding: 10px 16px;
    color: #f43f5e;
    font-weight: 600;
}
QPushButton#danger_btn:hover {
    background-color: #f43f5e;
    color: #ffffff;
    border-color: #f43f5e;
}
QPushButton#danger_btn:disabled {
    background-color: #12141c;
    border-color: #1c202a;
    color: #475569;
}

/* --- Success / Play Buttons --- */
QPushButton#success_btn {
    background-color: #122822;
    border: 1px solid #1a4d3f;
    border-radius: 8px;
    padding: 8px 16px;
    color: #10b981;
    font-weight: 600;
}
QPushButton#success_btn:hover {
    background-color: #10b981;
    color: #ffffff;
    border-color: #10b981;
}
QPushButton#success_btn:disabled {
    background-color: #12141c;
    border-color: #1c202a;
    color: #475569;
}

/* --- Checkboxes --- */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
    font-size: 9.5pt;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #33394d;
    background-color: #13151e;
}
QCheckBox::indicator:hover {
    border-color: #6366f1;
}
QCheckBox::indicator:checked {
    background-color: #6366f1;
    border-color: #6366f1;
}

/* --- Progress Bar --- */
QProgressBar {
    background-color: #13151e;
    border: 1px solid #232736;
    border-radius: 6px;
    text-align: center;
    color: transparent;
    height: 8px;
}
QProgressBar::chunk {
    background-color: #6366f1;
    border-radius: 5px;
}

/* --- List & History Widgets --- */
QListWidget {
    background-color: #11131a;
    border: 1px solid #212533;
    border-radius: 10px;
    padding: 6px;
    color: #f1f5f9;
}
QListWidget::item {
    background-color: #161924;
    border: 1px solid #222635;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 4px 2px;
}
QListWidget::item:hover {
    background-color: #1d2232;
    border-color: #333a50;
}
QListWidget::item:selected {
    background-color: #242a3e;
    border-color: #6366f1;
    color: #ffffff;
}

/* --- Text Logs --- */
QTextEdit#log_console {
    background-color: #0b0d13;
    border: 1px solid #1e2230;
    border-radius: 10px;
    padding: 12px;
    font-family: 'Consolas', 'Fira Code', monospace;
    font-size: 9pt;
    color: #94a3b8;
}

/* --- Tooltips --- */
QToolTip {
    background-color: #1e2230;
    border: 1px solid #3b4259;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f8fafc;
    font-size: 9pt;
}
"""


def get_card_style(is_active: bool = False, active_color: str = "#6366f1") -> str:
    """Helper to generate clean elevated card style with subtle 1px border."""
    if is_active:
        return f"""
            QFrame {{
                background-color: #171b28;
                border: 1.5px solid {active_color};
                border-radius: 12px;
            }}
        """
    return """
        QFrame {
            background-color: #141720;
            border: 1px solid #222635;
            border-radius: 12px;
        }
    """
