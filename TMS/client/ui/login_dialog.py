"""Login Dialog for Client Application"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox, QWidget
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor
from client.api_client import APIClient

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

QPushButton:disabled {
    background-color: #252525;
    color: #666666;
    border: 1px solid #2d2d2d;
}

QLineEdit, QTextEdit {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    padding: 8px 12px;
    color: #ffffff;
    font-size: 12px;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #0078d4;
    background-color: #252525;
}

QLabel {
    color: #ffffff;
    font-size: 12px;
}

QMessageBox {
    background-color: #1e1e1e;
}

QMessageBox QLabel {
    color: #ffffff;
}

QMessageBox QPushButton {
    min-width: 80px;
}
"""


class LoginDialog(QDialog):
    """Client login dialog with server status"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClient()
        self.logged_in = False
        self.user_data = None
        self.init_ui()
        self.check_server_status()
        
        # Auto-check server status every 5 seconds
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_server_status)
        self.status_timer.start(5000)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop timer when dialog closes
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
        event.accept()
    
    def init_ui(self):
        self.setWindowTitle("TMS Client - Login")
        self.setMinimumSize(450, 500)
        self.setStyleSheet(DARK_THEME)
        
        # Main layout with gradient background
        main_widget = QWidget()
        main_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1a1a1a, stop:1 #0f0f0f);
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(25)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Title Section
        title_widget = QWidget()
        title_widget.setStyleSheet("background: transparent;")
        title_layout = QVBoxLayout()
        title_layout.setSpacing(8)
        title_layout.setContentsMargins(0, 0, 0, 20)
        
        title = QLabel("🔐 TMS Client")
        title_font = QFont()
        title_font.setPointSize(28)
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
        title_layout.addWidget(title)
        
        subtitle = QLabel("Sign in to continue")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle.setFont(subtitle_font)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                color: #b0b0b0;
                background: transparent;
            }
        """)
        title_layout.addWidget(subtitle)
        
        title_widget.setLayout(title_layout)
        layout.addWidget(title_widget)
        
        # Server status - Enhanced
        status_widget = QWidget()
        status_widget.setStyleSheet("""
            QWidget {
                background: rgba(45, 45, 45, 0.5);
                border-radius: 10px;
                padding: 10px;
            }
        """)
        status_layout = QHBoxLayout()
        status_layout.setSpacing(12)
        status_layout.setContentsMargins(15, 10, 15, 10)
        
        status_label = QLabel("Server Status:")
        status_label.setStyleSheet("""
            QLabel {
                font-weight: 700;
                font-size: 13px;
                color: #e0e0e0;
                background: transparent;
            }
        """)
        status_layout.addWidget(status_label)
        
        self.status_indicator = QLabel("Checking...")
        self.status_indicator.setAlignment(Qt.AlignCenter)
        self.status_indicator.setStyleSheet("""
            QLabel {
                padding: 8px 20px;
                border-radius: 12px;
                font-weight: 700;
                font-size: 12px;
                background: #3d3d3d;
                color: #ffffff;
            }
        """)
        status_layout.addWidget(self.status_indicator)
        status_layout.addStretch()
        
        status_widget.setLayout(status_layout)
        layout.addWidget(status_widget)
        
        # Username - Enhanced
        username_label = QLabel("👤 Username:")
        username_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-weight: 600;
                font-size: 13px;
                background: transparent;
            }
        """)
        layout.addWidget(username_label)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setMinimumHeight(40)
        layout.addWidget(self.username_input)
        
        # Password - Enhanced
        password_label = QLabel("🔒 Password:")
        password_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-weight: 600;
                font-size: 13px;
                background: transparent;
            }
        """)
        layout.addWidget(password_label)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(40)
        self.password_input.returnPressed.connect(self.login)
        layout.addWidget(self.password_input)
        
        # Buttons - Enhanced
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        self.login_btn = QPushButton("🔓 Login")
        self.login_btn.setMinimumHeight(45)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0078d4, stop:1 #106ebe);
                border: 2px solid #0078d4;
                border-radius: 10px;
                color: white;
                font-size: 15px;
                font-weight: bold;
                padding: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #106ebe, stop:1 #005a9e);
                border: 2px solid #106ebe;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #005a9e, stop:1 #004578);
            }
            QPushButton:disabled {
                background: #2d2d2d;
                border: 2px solid #3d3d3d;
                color: #666666;
            }
        """)
        self.login_btn.clicked.connect(self.login)
        button_layout.addWidget(self.login_btn)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setMinimumHeight(45)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #3d3d3d, stop:1 #2d2d2d);
                border: 2px solid #3d3d3d;
                border-radius: 10px;
                color: white;
                font-size: 15px;
                font-weight: bold;
                padding: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #4d4d4d, stop:1 #3d3d3d);
                border: 2px solid #4d4d4d;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2d2d2d, stop:1 #1d1d1d);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        main_widget.setLayout(layout)
        
        main_container = QVBoxLayout()
        main_container.setContentsMargins(0, 0, 0, 0)
        main_container.addWidget(main_widget)
        self.setLayout(main_container)
    
    def check_server_status(self):
        """Check if server is online"""
        if self.api_client.ping():
            current_server = self.api_client.get_current_server()
            # Determine which server is connected
            if current_server:
                if "mominaembroidey.org.uk" in current_server:
                    server_name = "Remote Server"
                elif current_server.startswith("http://10."):
                    # ZeroTier IP (typically starts with 10.x.x.x)
                    server_name = "ZeroTier Server"
                else:
                    server_name = "Local Server"
            else:
                server_name = "Server"
            
            self.status_indicator.setText(f"🟢 {server_name} Online")
            self.status_indicator.setStyleSheet("""
                QLabel {
                    padding: 8px 20px;
                    border-radius: 12px;
                    font-weight: 700;
                    font-size: 12px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #2d5a2d, stop:1 #1f3f1f);
                    color: #90ee90;
                    border: 1px solid #3d7a3d;
                }
            """)
            self.login_btn.setEnabled(True)
        else:
            self.status_indicator.setText("🔴 Server Offline")
            self.status_indicator.setStyleSheet("""
                QLabel {
                    padding: 8px 20px;
                    border-radius: 12px;
                    font-weight: 700;
                    font-size: 12px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #5a2d2d, stop:1 #3f1f1f);
                    color: #ee9090;
                    border: 1px solid #7a3d3d;
                }
            """)
            self.login_btn.setEnabled(False)
    
    def login(self):
        """Perform login"""
        if not self.api_client.ping():
            current_server = self.api_client.get_current_server()
            server_info = f" at {current_server}" if current_server else ""
            error_msg = (
                f"Cannot connect to server{server_info}.\n\n"
                "Possible reasons:\n"
                "• ZeroTier is not connected\n"
                "• Server is down\n"
                "• Network connectivity issues\n\n"
                "Please check your connection and try again."
            )
            QMessageBox.warning(self, "Server Offline", error_msg)
            return
        
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Validation Error", "Please enter username and password.")
            return
        
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Logging in...")
        
        try:
            result = self.api_client.login(username, password)
            
            if result and result.get("success"):
                # Modules are now included in login response
                if "modules" not in result:
                    result["modules"] = []
                
                self.user_data = result
                self.logged_in = True
                QMessageBox.information(self, "Success", f"Login successful!\nRole: {result.get('role', 'USER')}")
                self.accept()
            else:
                error_msg = result.get("message", "Invalid credentials.") if result else "Connection error. Please check your network connection."
                QMessageBox.warning(self, "Login Failed", error_msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Login error: {str(e)}")
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("🔓 Login")

