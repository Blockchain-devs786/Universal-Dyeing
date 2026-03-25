"""Professional Dark Theme Styles for PyQt5"""

DARK_THEME = """
/* Main Window and Base Styles */
QMainWindow, QDialog, QWidget {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #1a1a1a, stop:1 #0f0f0f);
    color: #ffffff;
    font-family: 'Segoe UI', Arial, sans-serif;
}

/* Buttons - Professional Style */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #2d2d2d, stop:1 #1f1f1f);
    border: 1px solid #3d3d3d;
    border-radius: 8px;
    padding: 10px 20px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
    min-height: 36px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #3a3a3a, stop:1 #2d2d2d);
    border: 1px solid #4d4d4d;
    color: #ffffff;
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #1a1a1a, stop:1 #0f0f0f);
    border: 1px solid #2d2d2d;
}

QPushButton:disabled {
    background: #1a1a1a;
    color: #666666;
    border: 1px solid #2d2d2d;
}

/* Input Fields - Modern Style */
QLineEdit, QTextEdit {
    background: #252525;
    border: 2px solid #3d3d3d;
    border-radius: 8px;
    padding: 10px 14px;
    color: #ffffff;
    font-size: 13px;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
}

QLineEdit:focus, QTextEdit:focus {
    border: 2px solid #0078d4;
    background: #2a2a2a;
    outline: none;
}

QLineEdit:hover, QTextEdit:hover {
    border: 2px solid #4d4d4d;
}

/* Labels */
QLabel {
    color: #e0e0e0;
    font-size: 13px;
    font-weight: 400;
}

/* ComboBox - Enhanced */
QComboBox {
    background: #252525;
    border: 2px solid #3d3d3d;
    border-radius: 8px;
    padding: 10px 14px;
    color: #ffffff;
    font-size: 13px;
    min-height: 36px;
}

QComboBox:hover {
    border: 2px solid #4d4d4d;
    background: #2a2a2a;
}

QComboBox:focus {
    border: 2px solid #0078d4;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
    background: transparent;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #ffffff;
    width: 0;
    height: 0;
}

QComboBox QAbstractItemView {
    background: #252525;
    border: 2px solid #3d3d3d;
    border-radius: 8px;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
    padding: 4px;
}

/* Table Widget - Professional */
QTableWidget {
    background: #1a1a1a;
    border: 1px solid #3d3d3d;
    border-radius: 8px;
    gridline-color: #2d2d2d;
    color: #e0e0e0;
    font-size: 13px;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 8px;
    border: none;
}

QTableWidget::item:selected {
    background: #0078d4;
    color: #ffffff;
}

QTableWidget::item:hover {
    background: #2a2a2a;
}

QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #2d2d2d, stop:1 #1f1f1f);
    border: none;
    border-bottom: 2px solid #3d3d3d;
    padding: 10px;
    color: #ffffff;
    font-weight: 700;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ScrollBar - Modern */
QScrollBar:vertical {
    background: #1a1a1a;
    width: 14px;
    border: none;
    border-radius: 7px;
}

QScrollBar::handle:vertical {
    background: #3d3d3d;
    border-radius: 7px;
    min-height: 30px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: #4d4d4d;
}

QScrollBar::handle:vertical:pressed {
    background: #5d5d5d;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    border: none;
}

QScrollBar:horizontal {
    background: #1a1a1a;
    height: 14px;
    border: none;
    border-radius: 7px;
}

QScrollBar::handle:horizontal {
    background: #3d3d3d;
    border-radius: 7px;
    min-width: 30px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background: #4d4d4d;
}

/* Progress Bar */
QProgressBar {
    background: #252525;
    border: 1px solid #3d3d3d;
    border-radius: 8px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    height: 24px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #0078d4, stop:1 #106ebe);
    border-radius: 7px;
}

/* Message Box */
QMessageBox {
    background: #1a1a1a;
    border: 1px solid #3d3d3d;
    border-radius: 8px;
}

QMessageBox QLabel {
    color: #e0e0e0;
    font-size: 13px;
    padding: 10px;
}

QMessageBox QPushButton {
    min-width: 100px;
    padding: 8px 20px;
}

/* Tab Widget */
QTabWidget::pane {
    background: #1a1a1a;
    border: 1px solid #3d3d3d;
    border-radius: 8px;
}

QTabBar::tab {
    background: #252525;
    color: #b0b0b0;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background: #1a1a1a;
    color: #ffffff;
    border-bottom: 2px solid #0078d4;
}

QTabBar::tab:hover {
    background: #2a2a2a;
    color: #ffffff;
}
"""
