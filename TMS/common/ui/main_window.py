"""Main Application Window with Define, Data Entry, and Reports"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeyEvent
from common.ui.data_entry_window import DataEntryWindow
from common.ui.define_window import DefineWindow
from common.ui.reports_window import ReportsWindow

# Dark theme styles
DARK_THEME = """
QMainWindow, QDialog, QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
}

QPushButton {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    padding: 8px 16px;
    color: #ffffff;
    font-size: 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #3d3d3d;
    border: 1px solid #4d4d4d;
}

QPushButton:pressed {
    background-color: #1d1d1d;
}

QLabel {
    color: #ffffff;
    font-size: 12px;
}
"""


class MainApplicationWindow(QMainWindow):
    """Main application window with three main options"""
    
    def __init__(self, parent=None, dashboard_window=None, user_data=None):
        super().__init__(parent)
        self.data_entry_window = None
        self.define_window = None
        self.reports_window = None
        self.dashboard_window = dashboard_window
        self.user_data = user_data
        self.window_state_before_hide = None
        self.window_geometry_before_hide = None
        self.init_ui()
        
        # Install event filter for ESC key handling
        self.installEventFilter(self)
    
    def init_ui(self):
        self.setWindowTitle("TMS - Main Application")
        self.setMinimumSize(1200, 700)
        self.setStyleSheet(DARK_THEME)
        
        # Set window to full screen (covers entire screen including taskbar)
        self.showFullScreen()
        
        # Create central widget with gradient background
        central_widget = QWidget()
        central_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1a1a1a, stop:1 #0f0f0f);
            }
        """)
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        layout.setSpacing(40)
        layout.setContentsMargins(60, 50, 60, 50)
        
        # Header Section
        header_widget = QWidget()
        header_widget.setStyleSheet("background: transparent;")
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main Title
        title = QLabel("TMS - Main Application")
        title_font = QFont()
        title_font.setPointSize(32)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background: transparent;
                padding: 10px;
            }
        """)
        header_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Select a module to begin")
        subtitle_font = QFont()
        subtitle_font.setPointSize(14)
        subtitle.setFont(subtitle_font)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                color: #b0b0b0;
                background: transparent;
                padding: 5px;
            }
        """)
        header_layout.addWidget(subtitle)
        
        header_widget.setLayout(header_layout)
        layout.addWidget(header_widget)
        
        # Spacer
        layout.addStretch()
        
        # Three main buttons in a row
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(40)
        buttons_layout.setContentsMargins(80, 0, 80, 0)
        
        # Get user modules (default to all if admin or not set)
        user_modules = []
        if self.user_data:
            # Admins have access to all modules by default
            if self.user_data.get("role") == "ADMIN":
                user_modules = ["define", "data_entry", "reports"]
            else:
                user_modules = self.user_data.get("modules", [])
        
        # If no modules set and not admin, show all (for backward compatibility)
        if not user_modules:
            user_modules = ["define", "data_entry", "reports"]
        
        # Check if user has access to any sub-module in each section
        has_define_access = "define" in user_modules or any(m.startswith("define.") for m in user_modules)
        has_data_entry_access = "data_entry" in user_modules or any(m.startswith("data_entry.") for m in user_modules)
        has_reports_access = "reports" in user_modules or any(m.startswith("reports.") for m in user_modules)
        
        # Define Button
        self.define_btn = self.create_main_button("Define", "#0078d4", "⚙️")
        self.define_btn.clicked.connect(self.on_define_clicked)
        self.define_btn.setVisible(has_define_access)
        buttons_layout.addWidget(self.define_btn)
        
        # Data Entry Button
        self.data_entry_btn = self.create_main_button("Data Entry", "#107c10", "📝")
        self.data_entry_btn.clicked.connect(self.on_data_entry_clicked)
        self.data_entry_btn.setVisible(has_data_entry_access)
        buttons_layout.addWidget(self.data_entry_btn)
        
        # Reports Button
        self.reports_btn = self.create_main_button("Reports", "#d83b01", "📊")
        self.reports_btn.clicked.connect(self.on_reports_clicked)
        self.reports_btn.setVisible(has_reports_access)
        buttons_layout.addWidget(self.reports_btn)
        
        layout.addLayout(buttons_layout)
        
        # Spacer
        layout.addStretch()
        
        # Status label with better styling
        self.status_label = QLabel("Select an option to continue")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 14px;
                font-weight: 500;
                padding: 15px;
                background: rgba(45, 45, 45, 0.5);
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.status_label)
        
        central_widget.setLayout(layout)
        
        # Add user info label in bottom left corner
        self.setup_user_info()
    
    def setup_user_info(self):
        """Setup user info label in bottom left corner"""
        if not self.user_data:
            return
        
        # Get username and role from user_data
        username = self.user_data.get('username', 'Unknown')
        role = self.user_data.get('role', 'USER')
        
        # Create user info label
        self.user_info_label = QLabel(f"Login as '{username}' Role : {role}")
        self.user_info_label.setStyleSheet("""
            QLabel {
                color: #b0b0b0;
                font-size: 11px;
                padding: 5px 10px;
                background: rgba(45, 45, 45, 0.7);
                border-radius: 4px;
            }
        """)
        
        # Add to status bar or create a status bar
        if not self.statusBar():
            self.statusBar()
        self.statusBar().addPermanentWidget(self.user_info_label)
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #1e1e1e;
                border-top: 1px solid #3d3d3d;
                color: #ffffff;
            }
        """)
    
    def create_main_button(self, text: str, color: str, icon: str = "") -> QPushButton:
        """Create a large, beautiful rectangular button with gradient"""
        button = QPushButton(f"{icon}\n{text}" if icon else text)
        button.setMinimumSize(280, 240)
        button.setMaximumSize(320, 260)
        
        light_color = self._lighten_color(color)
        dark_color = self._darken_color(color)
        
        button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {light_color}, stop:1 {color});
                border: 2px solid {light_color};
                border-radius: 16px;
                color: white;
                font-size: 28px;
                font-weight: bold;
                padding: 25px;
                text-align: center;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {color}, stop:1 {dark_color});
                border: 2px solid {color};
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {dark_color}, stop:1 {color});
                border: 2px solid {dark_color};
            }}
        """)
        return button
    
    def _lighten_color(self, color: str) -> str:
        """Lighten a hex color"""
        # Simple lightening - add 20 to each RGB component
        r = min(255, int(color[1:3], 16) + 30)
        g = min(255, int(color[3:5], 16) + 30)
        b = min(255, int(color[5:7], 16) + 30)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _darken_color(self, color: str) -> str:
        """Darken a hex color"""
        # Simple darkening - subtract 20 from each RGB component
        r = max(0, int(color[1:3], 16) - 30)
        g = max(0, int(color[3:5], 16) - 30)
        b = max(0, int(color[5:7], 16) - 30)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def on_define_clicked(self):
        """Handle Define button click"""
        if self.define_window is None or not self.define_window.isVisible():
            # Create as top-level window (None parent) to keep Python instance in taskbar
            self.define_window = DefineWindow(None, user_data=self.user_data)
            self.define_window.main_window = self  # Store reference for returning
            self.define_window.showFullScreen()  # Show in full screen (covers entire screen including taskbar)
            self.hide()  # Hide main window
        else:
            self.define_window.showFullScreen()  # Ensure full screen (covers entire screen including taskbar)
            self.define_window.raise_()
            self.define_window.activateWindow()
    
    def on_data_entry_clicked(self):
        """Handle Data Entry button click"""
        if self.data_entry_window is None or not self.data_entry_window.isVisible():
            # Create as top-level window (None parent) to keep Python instance in taskbar
            self.data_entry_window = DataEntryWindow(None, user_data=self.user_data)
            self.data_entry_window.main_window = self  # Store reference for returning
            self.data_entry_window.showFullScreen()  # Show in full screen (covers entire screen including taskbar)
            self.hide()  # Hide main window
        else:
            self.data_entry_window.showFullScreen()  # Ensure full screen (covers entire screen including taskbar)
            self.data_entry_window.raise_()
            self.data_entry_window.activateWindow()
    
    def on_reports_clicked(self):
        """Handle Reports button click"""
        if self.reports_window is None or not self.reports_window.isVisible():
            # Create as top-level window (None parent) to keep Python instance in taskbar
            self.reports_window = ReportsWindow(None, user_data=self.user_data)
            self.reports_window.main_window = self  # Store reference for returning
            self.reports_window.showFullScreen()  # Show in full screen (covers entire screen including taskbar)
            self.hide()  # Hide main window
        else:
            self.reports_window.showFullScreen()  # Ensure full screen (covers entire screen including taskbar)
            self.reports_window.raise_()
            self.reports_window.activateWindow()
    
    def eventFilter(self, obj, event):
        """Handle ESC key events to return to dashboard and F11 to toggle full screen"""
        if event.type() == QKeyEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                self.return_to_dashboard()
                return True
            elif event.key() == Qt.Key_F11:
                # F11: Toggle full screen mode
                if self.isFullScreen():
                    self.showNormal()
                else:
                    self.showFullScreen()
                return True
        return super().eventFilter(obj, event)
    
    def return_to_dashboard(self):
        """Return to admin dashboard"""
        if self.dashboard_window:
            # Save current window state and geometry before hiding
            self.window_state_before_hide = self.windowState()
            self.window_geometry_before_hide = self.geometry()
            
            self.dashboard_window.show()
            self.dashboard_window.raise_()
            self.dashboard_window.activateWindow()
            self.hide()
    
    def showEvent(self, event):
        """Restore window state when shown"""
        super().showEvent(event)
        # Always show in full screen when opened (covers entire screen including taskbar)
        if not self.isMinimized():
            self.showFullScreen()
        elif self.window_state_before_hide is not None:
            # Restore geometry first
            if self.window_geometry_before_hide:
                self.setGeometry(self.window_geometry_before_hide)
            # Restore window state (minimized, maximized, etc.)
            self.setWindowState(self.window_state_before_hide)
            # Force update
            self.update()

