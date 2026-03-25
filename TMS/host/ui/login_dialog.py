"""Login Dialog for Host Application"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from host.db_pool import db_pool
from common.security import verify_password
from host.ui.styles import DARK_THEME


class LoginDialog(QDialog):
    """Admin login dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logged_in = False
        self.user_data = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("TMS Host - Login")
        self.setMinimumSize(400, 250)
        self.setStyleSheet(DARK_THEME)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("Admin Login")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Username
        username_label = QLabel("Username:")
        layout.addWidget(username_label)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel("Password:")
        layout.addWidget(password_label)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.login)
        layout.addWidget(self.password_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.login)
        button_layout.addWidget(login_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def login(self):
        """Perform login"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Validation Error", "Please enter username and password.")
            return
        
        conn = None
        try:
            conn = db_pool.get_connection()
            if not conn:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                return
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, username, password_hash, role, email FROM users WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()
            
            if not user:
                cursor.close()
                QMessageBox.warning(self, "Login Failed", "Invalid credentials.")
                return
            
            if not verify_password(password, user["password_hash"]):
                cursor.close()
                QMessageBox.warning(self, "Login Failed", "Invalid credentials.")
                return
            
            # Load user modules
            cursor.execute(
                "SELECT module_name FROM user_modules WHERE user_id = %s",
                (user["id"],)
            )
            user_modules = [row[0] for row in cursor.fetchall()]
            user["modules"] = user_modules
            cursor.close()
            
            self.user_data = user
            self.logged_in = True
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Login error: {str(e)}")
        finally:
            if conn:
                db_pool.return_connection(conn)

