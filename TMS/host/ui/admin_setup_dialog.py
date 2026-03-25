"""Admin Account Setup Dialog"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from host.db_pool import db_pool
from common.security import hash_password
from host.ui.styles import DARK_THEME


class AdminSetupDialog(QDialog):
    """First-run admin account setup dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Admin Account Setup")
        self.setMinimumSize(400, 300)
        self.setStyleSheet(DARK_THEME)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("Create Admin Account")
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
        
        # Email
        email_label = QLabel("Email:")
        layout.addWidget(email_label)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter email address")
        layout.addWidget(self.email_input)
        
        # Password
        password_label = QLabel("Password:")
        layout.addWidget(password_label)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        
        # Confirm Password
        confirm_label = QLabel("Confirm Password:")
        layout.addWidget(confirm_label)
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm password")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.confirm_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        create_btn = QPushButton("Create Admin")
        create_btn.clicked.connect(self.create_admin)
        button_layout.addWidget(create_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def create_admin(self):
        """Create admin account"""
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        
        # Validation
        if not username:
            QMessageBox.warning(self, "Validation Error", "Username is required.")
            return
        
        if not email or "@" not in email:
            QMessageBox.warning(self, "Validation Error", "Valid email is required.")
            return
        
        if not password or len(password) < 6:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters.")
            return
        
        if password != confirm:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match.")
            return
        
        # Create admin in database
        conn = None
        try:
            conn = db_pool.get_connection()
            if not conn:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                return
            
            cursor = conn.cursor()
            
            # Check if admin exists
            cursor.execute("SELECT id FROM users WHERE role = 'ADMIN'")
            if cursor.fetchone():
                QMessageBox.warning(self, "Admin Exists", "Admin account already exists.")
                cursor.close()
                return
            
            # Hash password
            password_hash = hash_password(password)
            
            # Insert admin
            cursor.execute(
                "INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
                (username, password_hash, email, "ADMIN")
            )
            conn.commit()
            cursor.close()
            
            QMessageBox.information(self, "Success", "Admin account created successfully!")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create admin: {str(e)}")
        finally:
            if conn:
                db_pool.return_connection(conn)

