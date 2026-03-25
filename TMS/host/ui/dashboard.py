"""Admin Dashboard Window"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QLineEdit, QComboBox, QStackedWidget,
    QCheckBox, QScrollArea, QGroupBox, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from host.db_pool import db_pool
from common.security import hash_password
from host.ui.styles import DARK_THEME
from common.ui.main_window import MainApplicationWindow


class CreateUserDialog(QDialog):
    """Dialog for creating new users"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Create User")
        self.setMinimumSize(500, 600)
        self.setStyleSheet(DARK_THEME + """
            QGroupBox {
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QCheckBox {
                color: #ffffff;
                padding: 5px;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        content_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Username
        layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)
        
        # Email
        layout.addWidget(QLabel("Email:"))
        self.email_input = QLineEdit()
        layout.addWidget(self.email_input)
        
        # Password
        layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        
        # Role
        layout.addWidget(QLabel("Role:"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(["USER", "ADMIN"])
        layout.addWidget(self.role_combo)
        
        # Module Access Section
        module_label = QLabel("Module Access:")
        module_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(module_label)
        
        # Module checkboxes with sub-modules
        self.module_checkboxes = {}
        self.submodule_checkboxes = {}
        
        # Define section
        define_group = QGroupBox("Define")
        define_layout = QVBoxLayout()
        define_checkbox = QCheckBox("Define")
        define_checkbox.setChecked(True)
        self.module_checkboxes["define"] = define_checkbox
        define_checkbox.stateChanged.connect(lambda state: self._toggle_submodules("define", state))
        define_layout.addWidget(define_checkbox)
        
        submodules_define = [
            ("define.liabilities", "  └─ Liabilities"),
            ("define.assets", "  └─ Assets"),
            ("define.expenses", "  └─ Expenses"),
            ("define.vendors", "  └─ Vendors")
        ]
        for submodule_code, submodule_label in submodules_define:
            sub_checkbox = QCheckBox(submodule_label)
            sub_checkbox.setChecked(True)
            self.submodule_checkboxes[submodule_code] = sub_checkbox
            define_layout.addWidget(sub_checkbox)
        define_group.setLayout(define_layout)
        layout.addWidget(define_group)
        
        # Data Entry section
        data_entry_group = QGroupBox("Data Entry")
        data_entry_layout = QVBoxLayout()
        data_entry_checkbox = QCheckBox("Data Entry")
        data_entry_checkbox.setChecked(True)
        self.module_checkboxes["data_entry"] = data_entry_checkbox
        data_entry_checkbox.stateChanged.connect(lambda state: self._toggle_submodules("data_entry", state))
        data_entry_layout.addWidget(data_entry_checkbox)
        
        submodules_data_entry = [
            ("data_entry.inward", "  └─ Inward"),
            ("data_entry.transfer", "  └─ Transfer"),
            ("data_entry.transfer_bn", "  └─ Transfer by Name"),
            ("data_entry.outward", "  └─ Outward"),
            ("data_entry.invoice", "  └─ Invoice")
        ]
        for submodule_code, submodule_label in submodules_data_entry:
            sub_checkbox = QCheckBox(submodule_label)
            sub_checkbox.setChecked(True)
            self.submodule_checkboxes[submodule_code] = sub_checkbox
            data_entry_layout.addWidget(sub_checkbox)
        data_entry_group.setLayout(data_entry_layout)
        layout.addWidget(data_entry_group)
        
        # Reports section
        reports_group = QGroupBox("Reports")
        reports_layout = QVBoxLayout()
        reports_checkbox = QCheckBox("Reports")
        reports_checkbox.setChecked(True)
        self.module_checkboxes["reports"] = reports_checkbox
        reports_checkbox.stateChanged.connect(lambda state: self._toggle_submodules("reports", state))
        reports_layout.addWidget(reports_checkbox)
        
        submodules_reports = [
            ("reports.stock", "  └─ Stock"),
            ("reports.stock_ledgers", "  └─ Stock Ledgers"),
            ("reports.cash_ledgers", "  └─ Cash Ledgers"),
            ("reports.vouchers", "  └─ Vouchers")
        ]
        for submodule_code, submodule_label in submodules_reports:
            sub_checkbox = QCheckBox(submodule_label)
            sub_checkbox.setChecked(True)
            self.submodule_checkboxes[submodule_code] = sub_checkbox
            reports_layout.addWidget(sub_checkbox)
        reports_group.setLayout(reports_layout)
        layout.addWidget(reports_group)
        
        content_widget.setLayout(layout)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # Buttons outside scroll area
        button_layout = QHBoxLayout()
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(create_btn)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def _toggle_submodules(self, section: str, state: int):
        """Enable/disable all submodules when section checkbox is toggled"""
        for submodule_code, checkbox in self.submodule_checkboxes.items():
            if submodule_code.startswith(section + "."):
                checkbox.setChecked(state == 2)  # 2 = Qt.Checked


class EditUserDialog(QDialog):
    """Dialog for editing existing users"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.init_ui()
        self.load_user_data()
    
    def init_ui(self):
        self.setWindowTitle("Edit User")
        self.setMinimumSize(500, 650)
        self.setStyleSheet(DARK_THEME + """
            QGroupBox {
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QCheckBox {
                color: #ffffff;
                padding: 5px;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        content_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # User ID (read-only)
        layout.addWidget(QLabel("User ID:"))
        self.id_label = QLabel()
        self.id_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.id_label)
        
        # Username
        layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)
        
        # Email
        layout.addWidget(QLabel("Email:"))
        self.email_input = QLineEdit()
        layout.addWidget(self.email_input)
        
        # Password (optional - leave blank to keep current)
        layout.addWidget(QLabel("New Password (leave blank to keep current):"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Leave blank to keep current password")
        layout.addWidget(self.password_input)
        
        # Role
        layout.addWidget(QLabel("Role:"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(["USER", "ADMIN"])
        layout.addWidget(self.role_combo)
        
        # Module Access Section
        module_label = QLabel("Module Access:")
        module_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(module_label)
        
        # Module checkboxes with sub-modules
        self.module_checkboxes = {}
        self.submodule_checkboxes = {}
        
        # Define section
        define_group = QGroupBox("Define")
        define_layout = QVBoxLayout()
        define_checkbox = QCheckBox("Define")
        self.module_checkboxes["define"] = define_checkbox
        define_checkbox.stateChanged.connect(lambda state: self._toggle_submodules("define", state))
        define_layout.addWidget(define_checkbox)
        
        submodules_define = [
            ("define.liabilities", "  └─ Liabilities"),
            ("define.assets", "  └─ Assets"),
            ("define.expenses", "  └─ Expenses"),
            ("define.vendors", "  └─ Vendors")
        ]
        for submodule_code, submodule_label in submodules_define:
            sub_checkbox = QCheckBox(submodule_label)
            self.submodule_checkboxes[submodule_code] = sub_checkbox
            define_layout.addWidget(sub_checkbox)
        define_group.setLayout(define_layout)
        layout.addWidget(define_group)
        
        # Data Entry section
        data_entry_group = QGroupBox("Data Entry")
        data_entry_layout = QVBoxLayout()
        data_entry_checkbox = QCheckBox("Data Entry")
        self.module_checkboxes["data_entry"] = data_entry_checkbox
        data_entry_checkbox.stateChanged.connect(lambda state: self._toggle_submodules("data_entry", state))
        data_entry_layout.addWidget(data_entry_checkbox)
        
        submodules_data_entry = [
            ("data_entry.inward", "  └─ Inward"),
            ("data_entry.transfer", "  └─ Transfer"),
            ("data_entry.transfer_bn", "  └─ Transfer by Name"),
            ("data_entry.outward", "  └─ Outward"),
            ("data_entry.invoice", "  └─ Invoice")
        ]
        for submodule_code, submodule_label in submodules_data_entry:
            sub_checkbox = QCheckBox(submodule_label)
            self.submodule_checkboxes[submodule_code] = sub_checkbox
            data_entry_layout.addWidget(sub_checkbox)
        data_entry_group.setLayout(data_entry_layout)
        layout.addWidget(data_entry_group)
        
        # Reports section
        reports_group = QGroupBox("Reports")
        reports_layout = QVBoxLayout()
        reports_checkbox = QCheckBox("Reports")
        self.module_checkboxes["reports"] = reports_checkbox
        reports_checkbox.stateChanged.connect(lambda state: self._toggle_submodules("reports", state))
        reports_layout.addWidget(reports_checkbox)
        
        submodules_reports = [
            ("reports.stock", "  └─ Stock"),
            ("reports.stock_ledgers", "  └─ Stock Ledgers"),
            ("reports.cash_ledgers", "  └─ Cash Ledgers"),
            ("reports.vouchers", "  └─ Vouchers")
        ]
        for submodule_code, submodule_label in submodules_reports:
            sub_checkbox = QCheckBox(submodule_label)
            self.submodule_checkboxes[submodule_code] = sub_checkbox
            reports_layout.addWidget(sub_checkbox)
        reports_group.setLayout(reports_layout)
        layout.addWidget(reports_group)
        
        content_widget.setLayout(layout)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # Buttons outside scroll area
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def _toggle_submodules(self, section: str, state: int):
        """Enable/disable all submodules when section checkbox is toggled"""
        for submodule_code, checkbox in self.submodule_checkboxes.items():
            if submodule_code.startswith(section + "."):
                checkbox.setChecked(state == 2)  # 2 = Qt.Checked
    
    def load_user_data(self):
        """Load existing user data into form"""
        self.id_label.setText(str(self.user_data["id"]))
        self.username_input.setText(self.user_data["username"])
        self.email_input.setText(self.user_data.get("email", ""))
        # Set role combo
        role_index = self.role_combo.findText(self.user_data["role"])
        if role_index >= 0:
            self.role_combo.setCurrentIndex(role_index)
        
        # Load user modules
        user_id = self.user_data["id"]
        conn = None
        try:
            conn = db_pool.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT module_name FROM user_modules WHERE user_id = %s",
                    (user_id,)
                )
                user_modules = [row[0] for row in cursor.fetchall()]
                cursor.close()
                
                # Set checkboxes based on user modules
                for module_code, checkbox in self.module_checkboxes.items():
                    checkbox.setChecked(module_code in user_modules)
                
                # Set sub-module checkboxes
                for submodule_code, checkbox in self.submodule_checkboxes.items():
                    checkbox.setChecked(submodule_code in user_modules)
        except Exception as e:
            print(f"Error loading user modules: {e}")
        finally:
            if conn:
                db_pool.return_connection(conn)


class DashboardWindow(QMainWindow):
    """Admin dashboard window"""
    
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.main_app_window = None
        self.window_state_before_hide = None
        self.window_geometry_before_hide = None
        self.init_ui()
        self.load_users()
        self.setup_user_info()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_users)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
    
    def init_ui(self):
        self.setWindowTitle(f"TMS Host - Admin Dashboard ({self.user_data['username']})")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(DARK_THEME)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left sidebar menu - Enhanced
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #1f1f1f, stop:1 #252525);
                border-right: 1px solid #3d3d3d;
            }
        """)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(15)
        sidebar_layout.setContentsMargins(15, 25, 15, 25)
        
        # Menu title with icon
        menu_title = QLabel("📋 Navigation")
        menu_title_font = QFont()
        menu_title_font.setPointSize(18)
        menu_title_font.setBold(True)
        menu_title.setFont(menu_title_font)
        menu_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                padding: 15px 10px;
                background: transparent;
                border-bottom: 2px solid #3d3d3d;
            }
        """)
        sidebar_layout.addWidget(menu_title)
        
        sidebar_layout.addWidget(QLabel())  # Spacer
        
        # Users button - Enhanced
        self.users_btn = QPushButton("👥 Users")
        self.users_btn.setMinimumHeight(50)
        self.users_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2d2d2d, stop:1 #1f1f1f);
                border: 1px solid #3d3d3d;
                border-radius: 10px;
                padding: 15px;
                color: #b0b0b0;
                font-size: 15px;
                font-weight: 600;
                text-align: left;
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
            }
        """)
        self.users_btn.clicked.connect(self.show_users_section)
        sidebar_layout.addWidget(self.users_btn)
        
        # Application button - Enhanced
        self.application_btn = QPushButton("🚀 Application")
        self.application_btn.setMinimumHeight(50)
        self.application_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2d2d2d, stop:1 #1f1f1f);
                border: 1px solid #3d3d3d;
                border-radius: 10px;
                padding: 15px;
                color: #b0b0b0;
                font-size: 15px;
                font-weight: 600;
                text-align: left;
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
            }
        """)
        self.application_btn.clicked.connect(self.show_application_section)
        sidebar_layout.addWidget(self.application_btn)
        
        sidebar_layout.addStretch()
        sidebar.setLayout(sidebar_layout)
        main_layout.addWidget(sidebar)
        
        # Right side - stacked widget for different sections
        self.stacked_widget = QStackedWidget()
        
        # Users section
        users_widget = self.create_users_section()
        self.stacked_widget.addWidget(users_widget)
        
        # Application section
        application_widget = self.create_application_section()
        self.stacked_widget.addWidget(application_widget)
        
        main_layout.addWidget(self.stacked_widget)
        
        central_widget.setLayout(main_layout)
        
        # Show users section by default
        self.show_users_section()
    
    def create_users_section(self) -> QWidget:
        """Create the users management section"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("User Management")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Buttons
        self.create_btn = QPushButton("Create User")
        self.create_btn.clicked.connect(self.create_user)
        header_layout.addWidget(self.create_btn)
        
        self.edit_btn = QPushButton("Edit User")
        self.edit_btn.clicked.connect(self.edit_user)
        header_layout.addWidget(self.edit_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_users)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels([
            "ID", "Username", "Email", "Role", "Created At"
        ])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.users_table.setSelectionMode(QTableWidget.SingleSelection)
        # Enable double-click to edit
        self.users_table.cellDoubleClicked.connect(self.edit_user)
        layout.addWidget(self.users_table)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888888; padding: 5px;")
        layout.addWidget(self.status_label)
        
        widget.setLayout(layout)
        return widget
    
    def create_application_section(self) -> QWidget:
        """Create the application section"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Title
        title = QLabel("Application")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Open Application button - Enhanced
        open_app_btn = QPushButton("🚀 Open Application")
        open_app_btn.setMinimumSize(350, 100)
        open_app_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0078d4, stop:1 #106ebe);
                border: 2px solid #0078d4;
                border-radius: 12px;
                color: white;
                font-size: 20px;
                font-weight: bold;
                padding: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #106ebe, stop:1 #005a9e);
                border: 2px solid #106ebe;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #005a9e, stop:1 #004578);
                border: 2px solid #005a9e;
            }
        """)
        open_app_btn.clicked.connect(self.open_main_application)
        layout.addWidget(open_app_btn, alignment=Qt.AlignCenter)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def show_users_section(self):
        """Show users management section"""
        self.stacked_widget.setCurrentIndex(0)
        self.users_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0078d4, stop:1 #106ebe);
                border: 2px solid #0078d4;
                border-radius: 10px;
                padding: 15px;
                color: #ffffff;
                font-size: 15px;
                font-weight: 700;
                text-align: left;
            }
        """)
        self.application_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2d2d2d, stop:1 #1f1f1f);
                border: 1px solid #3d3d3d;
                border-radius: 10px;
                padding: 15px;
                color: #b0b0b0;
                font-size: 15px;
                font-weight: 600;
                text-align: left;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #3a3a3a, stop:1 #2d2d2d);
                border: 1px solid #4d4d4d;
                color: #ffffff;
            }
        """)
    
    def show_application_section(self):
        """Show application section"""
        self.stacked_widget.setCurrentIndex(1)
        self.application_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0078d4, stop:1 #106ebe);
                border: 2px solid #0078d4;
                border-radius: 10px;
                padding: 15px;
                color: #ffffff;
                font-size: 15px;
                font-weight: 700;
                text-align: left;
            }
        """)
        self.users_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2d2d2d, stop:1 #1f1f1f);
                border: 1px solid #3d3d3d;
                border-radius: 10px;
                padding: 15px;
                color: #b0b0b0;
                font-size: 15px;
                font-weight: 600;
                text-align: left;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #3a3a3a, stop:1 #2d2d2d);
                border: 1px solid #4d4d4d;
                color: #ffffff;
            }
        """)
    
    def open_main_application(self):
        """Open the main application window"""
        # Save current window state and geometry before hiding
        self.window_state_before_hide = self.windowState()
        self.window_geometry_before_hide = self.geometry()
        
        if self.main_app_window is None or not self.main_app_window.isVisible():
            # Create main app window with reference to this dashboard and user data
            self.main_app_window = MainApplicationWindow(parent=None, dashboard_window=self, user_data=self.user_data)
            self.main_app_window.show()
            self.hide()  # Hide dashboard when opening application
        else:
            self.main_app_window.raise_()
            self.main_app_window.activateWindow()
            self.hide()  # Hide dashboard
    
    def showEvent(self, event):
        """Restore window state when shown"""
        super().showEvent(event)
        if self.window_state_before_hide is not None:
            # Restore geometry first
            if self.window_geometry_before_hide:
                self.setGeometry(self.window_geometry_before_hide)
            # Restore window state (minimized, maximized, etc.)
            self.setWindowState(self.window_state_before_hide)
            # Force update
            self.update()
    
    def setup_user_info(self):
        """Setup user info label in bottom left corner"""
        if not self.user_data:
            return
        
        # Get username and role from user_data
        username = self.user_data.get('username', 'Unknown')
        role = self.user_data.get('role', 'USER')
        
        # Create user info label
        user_info_label = QLabel(f"Login as '{username}' Role : {role}")
        user_info_label.setStyleSheet("""
            QLabel {
                color: #b0b0b0;
                font-size: 11px;
                padding: 5px 10px;
                background: rgba(45, 45, 45, 0.7);
                border-radius: 4px;
            }
        """)
        
        # Add to status bar
        if not self.statusBar():
            self.statusBar()
        self.statusBar().addPermanentWidget(user_info_label)
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #1e1e1e;
                border-top: 1px solid #3d3d3d;
                color: #ffffff;
            }
        """)
    
    def load_users(self):
        """Load users from database"""
        conn = None
        try:
            conn = db_pool.get_connection()
            if not conn:
                self.status_label.setText("Database connection failed")
                return
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, username, email, role, created_at FROM users ORDER BY id"
            )
            users = cursor.fetchall()
            cursor.close()
            
            self.users_table.setRowCount(len(users))
            for row, user in enumerate(users):
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user["id"])))
                self.users_table.setItem(row, 1, QTableWidgetItem(user["username"]))
                self.users_table.setItem(row, 2, QTableWidgetItem(user.get("email", "")))
                self.users_table.setItem(row, 3, QTableWidgetItem(user["role"]))
                created_at = user.get("created_at", "")
                if created_at:
                    created_at = str(created_at).split()[0]  # Date only
                self.users_table.setItem(row, 4, QTableWidgetItem(created_at))
            
            self.status_label.setText(f"Loaded {len(users)} users")
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load users: {str(e)}")
        finally:
            if conn:
                db_pool.return_connection(conn)
    
    def create_user(self):
        """Show create user dialog"""
        dialog = CreateUserDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            username = dialog.username_input.text().strip()
            email = dialog.email_input.text().strip()
            password = dialog.password_input.text()
            role = dialog.role_combo.currentText()
            
            if not username or not email or not password:
                QMessageBox.warning(self, "Validation Error", "All fields are required.")
                return
            
            if len(password) < 6:
                QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters.")
                return
            
            conn = None
            try:
                conn = db_pool.get_connection()
                if not conn:
                    QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                    return
                
                cursor = conn.cursor()
                
                # Check if username exists
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cursor.fetchone():
                    QMessageBox.warning(self, "Error", "Username already exists.")
                    cursor.close()
                    return
                
                # Hash password
                password_hash = hash_password(password)
                
                # Insert user
                cursor.execute(
                    "INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
                    (username, password_hash, email, role)
                )
                user_id = cursor.lastrowid
                
                # Save selected modules and sub-modules
                selected_modules = []
                # Add section modules if checked
                for module_code, checkbox in dialog.module_checkboxes.items():
                    if checkbox.isChecked():
                        selected_modules.append(module_code)
                # Add sub-modules if checked
                for submodule_code, checkbox in dialog.submodule_checkboxes.items():
                    if checkbox.isChecked():
                        selected_modules.append(submodule_code)
                
                for module_code in selected_modules:
                    cursor.execute(
                        "INSERT INTO user_modules (user_id, module_name) VALUES (%s, %s)",
                        (user_id, module_code)
                    )
                
                conn.commit()
                cursor.close()
                
                QMessageBox.information(self, "Success", "User created successfully!")
                self.load_users()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create user: {str(e)}")
            finally:
                if conn:
                    db_pool.return_connection(conn)
    
    def edit_user(self):
        """Show edit user dialog"""
        selected_rows = self.users_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a user to edit.")
            return
        
        row = selected_rows[0].row()
        user_id = int(self.users_table.item(row, 0).text())
        
        # Get full user data from database
        conn = None
        try:
            conn = db_pool.get_connection()
            if not conn:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                return
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, username, email, role FROM users WHERE id = %s",
                (user_id,)
            )
            user_data = cursor.fetchone()
            cursor.close()
            
            if not user_data:
                QMessageBox.warning(self, "Error", "User not found.")
                return
            
            # Show edit dialog
            dialog = EditUserDialog(user_data, self)
            if dialog.exec_() == QDialog.Accepted:
                username = dialog.username_input.text().strip()
                email = dialog.email_input.text().strip()
                password = dialog.password_input.text()
                role = dialog.role_combo.currentText()
                
                if not username or not email:
                    QMessageBox.warning(self, "Validation Error", "Username and email are required.")
                    return
                
                # Validate password if provided
                if password and len(password) < 6:
                    QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters.")
                    return
                
                # Update user
                cursor = conn.cursor()
                
                # Check if username is taken by another user
                cursor.execute(
                    "SELECT id FROM users WHERE username = %s AND id != %s",
                    (username, user_id)
                )
                if cursor.fetchone():
                    QMessageBox.warning(self, "Error", "Username already taken by another user.")
                    cursor.close()
                    return
                
                # Update user data
                if password:
                    # Update with new password
                    password_hash = hash_password(password)
                    cursor.execute(
                        "UPDATE users SET username = %s, email = %s, password_hash = %s, role = %s WHERE id = %s",
                        (username, email, password_hash, role, user_id)
                    )
                else:
                    # Update without changing password
                    cursor.execute(
                        "UPDATE users SET username = %s, email = %s, role = %s WHERE id = %s",
                        (username, email, role, user_id)
                    )
                
                # Update user modules - delete existing and insert new
                cursor.execute("DELETE FROM user_modules WHERE user_id = %s", (user_id,))
                selected_modules = []
                # Add section modules if checked
                for module_code, checkbox in dialog.module_checkboxes.items():
                    if checkbox.isChecked():
                        selected_modules.append(module_code)
                # Add sub-modules if checked
                for submodule_code, checkbox in dialog.submodule_checkboxes.items():
                    if checkbox.isChecked():
                        selected_modules.append(submodule_code)
                
                for module_code in selected_modules:
                    cursor.execute(
                        "INSERT INTO user_modules (user_id, module_name) VALUES (%s, %s)",
                        (user_id, module_code)
                    )
                
                conn.commit()
                cursor.close()
                
                QMessageBox.information(self, "Success", "User updated successfully!")
                
                # If admin edited their own account, update local user_data
                if user_id == self.user_data["id"]:
                    self.user_data["username"] = username
                    self.user_data["email"] = email
                    self.user_data["role"] = role
                    self.setWindowTitle(f"TMS Host - Admin Dashboard ({username})")
                
                self.load_users()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update user: {str(e)}")
        finally:
            if conn:
                db_pool.return_connection(conn)

