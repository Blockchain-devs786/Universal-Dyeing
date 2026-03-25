"""License Activation Dialog"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from host.license_manager import LicenseManager
from host.email_service import EmailService
from host.ui.styles import DARK_THEME


class EmailThread(QThread):
    """Thread for email operations"""
    finished = pyqtSignal(bool, str, int)  # success, message, validity_days
    progress = pyqtSignal(str)
    
    def __init__(self, operation, machine_id):
        super().__init__()
        self.operation = operation
        self.machine_id = machine_id
        self.email_service = EmailService()
    
    def run(self):
        if self.operation == "send":
            self.progress.emit("Sending license request...")
            success = self.email_service.send_license_request(self.machine_id)
            if success:
                self.finished.emit(True, "License request sent successfully!", 0)
            else:
                self.finished.emit(False, "Failed to send license request.", 0)
        elif self.operation == "check":
            self.progress.emit("Checking inbox for reply...")
            validity_days = self.email_service.check_for_reply(self.machine_id)
            if validity_days:
                self.finished.emit(True, f"License activated! Validity: {validity_days} days", validity_days)
            else:
                self.finished.emit(False, "No license reply found in inbox.", 0)


class LicenseDialog(QDialog):
    """License activation dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.license_manager = LicenseManager()
        self.email_service = EmailService()
        self.email_thread = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("TMS License Activation")
        self.setMinimumSize(500, 400)
        self.setStyleSheet(DARK_THEME)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("License Activation Required")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Status label
        self.status_label = QLabel("Your license has expired or is missing.")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Machine ID display
        machine_id_label = QLabel(f"Machine ID: {self.license_manager.machine_id[:16]}...")
        machine_id_label.setAlignment(Qt.AlignCenter)
        machine_id_label.setStyleSheet("color: #888888; font-size: 10px;")
        layout.addWidget(machine_id_label)
        
        # Instructions
        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setMaximumHeight(120)
        instructions.setPlainText(
            "To activate your license:\n\n"
            "1. Click 'Send License Request' to email your activation request\n"
            "2. Wait for a reply email with validity days\n"
            "3. Click 'Check For Reply' to activate your license"
        )
        layout.addWidget(instructions)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.send_btn = QPushButton("Send License Request")
        self.send_btn.clicked.connect(self.send_request)
        button_layout.addWidget(self.send_btn)
        
        self.check_btn = QPushButton("Check For Reply")
        self.check_btn.clicked.connect(self.check_reply)
        button_layout.addWidget(self.check_btn)
        
        layout.addLayout(button_layout)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def send_request(self):
        """Send license request email"""
        self.send_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        
        self.email_thread = EmailThread("send", self.license_manager.machine_id)
        self.email_thread.finished.connect(self.on_email_finished)
        self.email_thread.progress.connect(self.on_progress)
        self.email_thread.start()
    
    def check_reply(self):
        """Check for license reply"""
        self.send_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        
        self.email_thread = EmailThread("check", self.license_manager.machine_id)
        self.email_thread.finished.connect(self.on_check_finished)
        self.email_thread.progress.connect(self.on_progress)
        self.email_thread.start()
    
    def on_progress(self, message):
        """Update progress message"""
        self.status_label.setText(message)
    
    def on_email_finished(self, success, message):
        """Handle email send completion"""
        self.progress_bar.setVisible(False)
        self.send_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        
        msg = QMessageBox(self)
        msg.setWindowTitle("License Request")
        msg.setText(message)
        msg.exec_()
    
    def on_check_finished(self, success, message, validity_days):
        """Handle check reply completion"""
        self.progress_bar.setVisible(False)
        self.send_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        
        if success and validity_days > 0:
            # Save license
            if self.license_manager.save_license("", "HOST", validity_days):
                msg = QMessageBox(self)
                msg.setWindowTitle("License Activated")
                msg.setText("License activated successfully! Please restart the application.")
                msg.exec_()
                self.accept()
            else:
                msg = QMessageBox(self)
                msg.setWindowTitle("Error")
                msg.setText("Failed to save license file.")
                msg.exec_()
        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("No Reply Found")
            msg.setText(message)
            msg.exec_()

