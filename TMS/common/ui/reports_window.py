"""Reports Window with Stock Reports"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QGraphicsBlurEffect
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QPoint
from PyQt5.QtGui import QFont, QKeyEvent
from host.ui.styles import DARK_THEME
from common.ui.data_entry_modules_transfer_outward_stock import StockModule


class WelcomeScreen(QWidget):
    """Welcome screen for Reports"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addStretch()
        
        welcome_label = QLabel("Welcome to Reports")
        welcome_font = QFont()
        welcome_font.setPointSize(36)
        welcome_font.setBold(True)
        welcome_label.setFont(welcome_font)
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background: transparent;
                padding: 30px;
            }
        """)
        layout.addWidget(welcome_label)
        
        hint_label = QLabel("Press ESC to view available reports")
        hint_font = QFont()
        hint_font.setPointSize(14)
        hint_label.setFont(hint_font)
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("""
            QLabel {
                color: #888888;
                background: transparent;
                padding: 10px;
            }
        """)
        layout.addWidget(hint_label)
        
        layout.addStretch()
        self.setLayout(layout)


class AnimatedSidebar(QWidget):
    """Animated sidebar widget for Reports"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setFixedWidth(250)
        self.hide()
        
        # Animation setup
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #1f1f1f, stop:1 #252525);
                border-right: 2px solid #3d3d3d;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 30, 20, 30)
        
        # Title
        title = QLabel("📊 Reports")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background: transparent;
                padding: 15px 10px;
                border-bottom: 2px solid #3d3d3d;
            }
        """)
        layout.addWidget(title)
        
        layout.addWidget(QLabel())  # Spacer
        
        # Module buttons
        self.stock_btn = self.create_module_button("📦 Stock")
        layout.addWidget(self.stock_btn)
        
        self.stock_ledgers_btn = self.create_module_button("📋 Stock Ledgers")
        layout.addWidget(self.stock_ledgers_btn)
        
        self.cash_ledgers_btn = self.create_module_button("💰 Cash Ledgers")
        layout.addWidget(self.cash_ledgers_btn)
        
        self.vouchers_btn = self.create_module_button("📝 Vouchers")
        layout.addWidget(self.vouchers_btn)
        
        layout.addStretch()
        
        # Hint
        hint = QLabel("Press ESC again to exit")
        hint.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 11px;
                background: transparent;
                padding: 10px;
            }
        """)
        layout.addWidget(hint)
        
        self.setLayout(layout)
    
    def create_module_button(self, text: str) -> QPushButton:
        """Create a module navigation button"""
        btn = QPushButton(text)
        btn.setMinimumHeight(55)
        btn.setStyleSheet("""
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
                border: 1px solid #0078d4;
                color: #ffffff;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1a1a1a, stop:1 #0f0f0f);
            }
        """)
        return btn
    
    def show_animated(self):
        """Show sidebar with animation"""
        if self.isVisible():
            return
        
        parent = self.parent()
        if parent:
            self.setGeometry(-self.width(), 0, self.width(), parent.height())
            self.show()
            self.raise_()
            
            start_pos = QPoint(-self.width(), 0)
            end_pos = QPoint(0, 0)
            
            try:
                self.animation.finished.disconnect()
            except TypeError:
                pass
            
            self.animation.setStartValue(start_pos)
            self.animation.setEndValue(end_pos)
            self.animation.start()
    
    def hide_animated(self):
        """Hide sidebar with animation"""
        if not self.isVisible():
            return
        
        start_pos = self.pos()
        end_pos = QPoint(-self.width(), 0)
        
        try:
            self.animation.finished.disconnect()
        except TypeError:
            pass
        
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.finished.connect(self._on_hide_finished)
        self.animation.start()
    
    def _on_hide_finished(self):
        """Called when hide animation finishes"""
        self.hide()
        try:
            self.animation.finished.disconnect(self._on_hide_finished)
        except TypeError:
            pass


class ReportsWindow(QMainWindow):
    """Reports Window with ESC key navigation"""
    
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.parent_window = parent
        self.user_data = user_data
        self.esc_press_time = 0
        self.esc_double_click_threshold = 500  # milliseconds
        self.blur_effect = None
        self.init_ui()
        self.setup_user_info()
    
    def init_ui(self):
        self.setWindowTitle("TMS - Reports")
        self.setMinimumSize(1200, 700)
        self.setStyleSheet(DARK_THEME)
        
        # Set window to full screen
        self.showFullScreen()
        
        # Central widget container
        central_widget = QWidget()
        central_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1a1a1a, stop:1 #0f0f0f);
            }
        """)
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Stacked widget for content
        self.stacked_widget = QStackedWidget()
        
        # Welcome screen (index 0)
        welcome_screen = WelcomeScreen()
        self.stacked_widget.addWidget(welcome_screen)
        
        # Sidebar (created before modules to check permissions)
        self.sidebar = AnimatedSidebar(central_widget)
        
        # Check user permissions
        user_modules = self.user_data.get("modules", []) if self.user_data else []
        is_admin = self.user_data.get("role") == "ADMIN" if self.user_data else False
        
        # Modules - check permissions before adding
        self.module_indices = {}  # Track which index each module is at
        current_index = 1  # Start after welcome screen (index 0)
        
        # Stock module - check permissions
        if is_admin or "reports.stock" in user_modules or "reports" in user_modules:
            self.stacked_widget.addWidget(StockModule(user_data=self.user_data))
            module_index = current_index
            self.module_indices["stock"] = module_index
            self.sidebar.stock_btn.clicked.connect(lambda checked, idx=module_index: self.show_module(idx))
            current_index += 1
        else:
            # User doesn't have access to stock module
            self.sidebar.stock_btn.setVisible(False)
        
        # Stock Ledgers module - check permissions
        if is_admin or "reports.stock_ledgers" in user_modules or "reports" in user_modules:
            from common.ui.stock_ledgers_module import StockLedgersModule
            self.stacked_widget.addWidget(StockLedgersModule(user_data=self.user_data))
            module_index = current_index
            self.module_indices["stock_ledgers"] = module_index
            self.sidebar.stock_ledgers_btn.clicked.connect(lambda checked, idx=module_index: self.show_module(idx))
            current_index += 1
        else:
            # User doesn't have access to stock ledgers module
            self.sidebar.stock_ledgers_btn.setVisible(False)
        
        # Cash Ledgers module - check permissions
        if is_admin or "reports.cash_ledgers" in user_modules or "reports" in user_modules:
            from common.ui.cash_ledgers_module import CashLedgersModule
            self.stacked_widget.addWidget(CashLedgersModule(user_data=self.user_data))
            module_index = current_index
            self.module_indices["cash_ledgers"] = module_index
            self.sidebar.cash_ledgers_btn.clicked.connect(lambda checked, idx=module_index: self.show_module(idx))
            current_index += 1
        else:
            # User doesn't have access to cash ledgers module
            self.sidebar.cash_ledgers_btn.setVisible(False)
        
        # Vouchers module - check permissions
        if is_admin or "reports.vouchers" in user_modules or "reports" in user_modules:
            from common.ui.voucher_module import VoucherModule
            self.stacked_widget.addWidget(VoucherModule(user_data=self.user_data))
            module_index = current_index
            self.module_indices["vouchers"] = module_index
            self.sidebar.vouchers_btn.clicked.connect(lambda checked, idx=module_index: self.show_module(idx))
            current_index += 1
        else:
            # User doesn't have access to vouchers module
            self.sidebar.vouchers_btn.setVisible(False)
        
        # Add stacked widget to layout
        main_layout.addWidget(self.stacked_widget)
        
        central_widget.setLayout(main_layout)
        
        # Install event filter for ESC key handling
        self.installEventFilter(self)
    
    def setup_user_info(self):
        """Setup user info label in bottom left corner"""
        if not self.user_data:
            return
        
        username = self.user_data.get('username', 'Unknown')
        role = self.user_data.get('role', 'USER')
        
        from PyQt5.QtWidgets import QLabel
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
    
    def eventFilter(self, obj, event):
        """Handle ESC key events and F11 to toggle full screen"""
        if event.type() == QKeyEvent.KeyPress:
            if event.key() == Qt.Key_F11:
                if self.isFullScreen():
                    self.showNormal()
                else:
                    self.showFullScreen()
                return True
            elif event.key() == Qt.Key_Escape:
                self.handle_esc_key()
                return True
        return super().eventFilter(obj, event)
    
    def handle_esc_key(self):
        """Handle ESC key press logic"""
        import time
        current_time = time.time() * 1000
        
        # Check for double ESC (exit to main window)
        if self.esc_press_time > 0:
            time_diff = current_time - self.esc_press_time
            if time_diff < self.esc_double_click_threshold:
                # Double ESC - exit to main window
                self.exit_to_main_window()
                self.esc_press_time = 0
                return
        
        self.esc_press_time = current_time
        
        # Single ESC logic
        if self.sidebar.isVisible():
            self.hide_sidebar()
        else:
            self.show_sidebar()
    
    def show_sidebar(self):
        """Show sidebar and blur content"""
        self.sidebar.show_animated()
        self.apply_blur_effect()
    
    def hide_sidebar(self):
        """Hide sidebar and remove blur"""
        self.sidebar.hide_animated()
        self.remove_blur_effect()
    
    def show_module(self, index: int):
        """Show selected module"""
        if index < 0 or index >= self.stacked_widget.count():
            return
        
        # Switch to module (index is already correct)
        self.stacked_widget.setCurrentIndex(index)
        
        # Hide sidebar and remove blur
        self.hide_sidebar()
    
    def apply_blur_effect(self):
        """Apply blur effect to current widget"""
        current_widget = self.stacked_widget.currentWidget()
        if current_widget:
            if self.blur_effect:
                current_widget.setGraphicsEffect(None)
            
            self.blur_effect = QGraphicsBlurEffect()
            self.blur_effect.setBlurRadius(10)
            current_widget.setGraphicsEffect(self.blur_effect)
    
    def remove_blur_effect(self):
        """Remove blur effect from current widget"""
        current_widget = self.stacked_widget.currentWidget()
        if current_widget:
            current_widget.setGraphicsEffect(None)
            self.blur_effect = None
    
    def exit_to_main_window(self):
        """Exit to main window"""
        main_window = getattr(self, 'main_window', self.parent_window)
        if main_window:
            main_window.showFullScreen()
            main_window.raise_()
            main_window.activateWindow()
        self.close()
    
    def showEvent(self, event):
        """Ensure window is full screen when shown"""
        super().showEvent(event)
        if not self.isMinimized():
            self.showFullScreen()

