"""Define Window with Master Management (Liabilities, Assets, Expenses, Vendors)"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QLineEdit, QFormLayout, QDialogButtonBox, QMessageBox, QTextEdit,
    QDoubleSpinBox, QAbstractItemView, QGraphicsBlurEffect
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QThread, pyqtSignal
import time
from PyQt5.QtGui import QFont, QKeyEvent
import requests
from common.config import CLIENT_FALLBACK_SERVER
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

QLabel {
    color: #ffffff;
    font-size: 12px;
}
"""


class WelcomeScreen(QWidget):
    """Welcome screen for Define section"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("Welcome to Define")
        title_font = QFont()
        title_font.setPointSize(36)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background: transparent;
                padding: 20px;
            }
        """)
        
        subtitle = QLabel("Select a module from the sidebar to begin")
        subtitle_font = QFont()
        subtitle_font.setPointSize(16)
        subtitle.setFont(subtitle_font)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                color: #b0b0b0;
                background: transparent;
                padding: 10px;
            }
        """)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        self.setLayout(layout)


class AnimatedSidebar(QWidget):
    """Animated sidebar for Define section"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.is_visible = False
        self.init_ui()
        
        # Animation
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Start hidden
        self.hide()
    
    def init_ui(self):
        self.setFixedWidth(250)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #2a2a2a, stop:1 #1f1f1f);
                border-right: 2px solid #3d3d3d;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 30, 20, 30)
        
        # Title
        title = QLabel("Define Modules")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff; padding: 10px;")
        layout.addWidget(title)
        
        layout.addWidget(QLabel(""))  # Spacer
        
        # Liabilities Button (renamed from Party)
        self.party_btn = QPushButton("📘 Liabilities")
        self.party_btn.setMinimumHeight(50)
        self.party_btn.setStyleSheet("""
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
        layout.addWidget(self.party_btn)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def show_sidebar(self):
        """Animate sidebar in"""
        if self.is_visible:
            return
        
        self.is_visible = True
        parent_rect = self.parent_widget.geometry()
        
        start_rect = QRect(-250, 0, 250, parent_rect.height())
        end_rect = QRect(0, 0, 250, parent_rect.height())
        
        self.setGeometry(start_rect)
        self.show()
        self.raise_()  # Ensure sidebar is on top
        
        self.animation.setStartValue(start_rect)
        self.animation.setEndValue(end_rect)
        self.animation.start()
    
    def hide_sidebar(self):
        """Animate sidebar out"""
        if not self.is_visible:
            return
        
        self.is_visible = False
        parent_rect = self.parent_widget.geometry()
        
        start_rect = QRect(0, 0, 250, parent_rect.height())
        end_rect = QRect(-250, 0, 250, parent_rect.height())
        
        self.animation.setStartValue(start_rect)
        self.animation.setEndValue(end_rect)
        self.animation.finished.connect(self._on_hide_finished)
        self.animation.start()
    
    def _on_hide_finished(self):
        """Called when hide animation finishes"""
        self.hide()
        try:
            self.animation.finished.disconnect()
        except TypeError:
            pass


class PartyLoadThread(QThread):
    """Background thread to load liabilities from API (reuses party API)"""
    finished = pyqtSignal(object, bool)  # parties list, server_available
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
    
    def run(self):
        """Load parties in background thread using connection pooling"""
        try:
            result = self.api_client.get_parties()
            if result and result.get("success"):
                parties = result.get("parties", [])
                self.finished.emit(parties, True)
            else:
                self.finished.emit([], False)
        except Exception as e:
            # Error - return empty list
            self.finished.emit([], False)


class PartyModule(QWidget):
    """Liabilities master module (reuses Party backend API)"""
    
    def __init__(self, user_data=None):
        super().__init__()
        self.user_data = user_data
        self.ws_bus = (user_data or {}).get("ws_bus")
        self.parties = []
        self.server_available = False
        self.load_thread = None
        # Initialize API client with connection pooling
        from client.api_client import APIClient
        self.api_client = APIClient()
        self.init_ui()
        if self.ws_bus:
            try:
                self.ws_bus.message.connect(self.on_realtime_message)
            except Exception:
                pass
        # Load parties in background thread after UI is ready
        self.load_parties_async()

    def on_realtime_message(self, message: dict):
        """Apply server-pushed CRUD updates (so client UIs update instantly)."""
        if not isinstance(message, dict):
            return
        if message.get("type") != "entity_change":
            return
        if message.get("entity") != "party":
            return

        action = message.get("action")
        data = message.get("data") or {}
        if action in ("created", "updated"):
            if isinstance(data, dict) and data.get("id"):
                self._upsert_party(data)
        elif action in ("deleted", "deactivated"):
            party_id = None
            if isinstance(data, dict):
                party_id = data.get("id")
            if party_id:
                self._deactivate_party_by_id(party_id)

    def _upsert_party(self, party: dict):
        """Insert or update party in-memory and refresh table."""
        # Safety check: ensure widget still exists
        if not hasattr(self, 'table') or self.table is None:
            return
        try:
            _ = self.table.objectName()
        except RuntimeError:
            # Widget was deleted, ignore update
            return
        
        if not hasattr(self, "all_parties") or self.all_parties is None:
            self.all_parties = []
        if not hasattr(self, "parties") or self.parties is None:
            self.parties = []

        party_id = party.get("id")
        if not party_id:
            return

        def _replace_or_add(lst):
            idx = next((i for i, p in enumerate(lst) if p.get("id") == party_id), None)
            if idx is None:
                lst.append(party)
            else:
                lst[idx] = party

        _replace_or_add(self.parties)
        _replace_or_add(self.all_parties)
        self.filter_table()

    def _deactivate_party_by_id(self, party_id: int):
        """Mark party as inactive in-memory and refresh table (shows in red)."""
        if not hasattr(self, 'table') or self.table is None:
            return
        try:
            _ = self.table.objectName()
        except RuntimeError:
            return
        for p in (self.parties or []):
            if p.get('id') == party_id:
                p['is_active'] = False
                break
        for p in (self.all_parties or []):
            if p.get('id') == party_id:
                p['is_active'] = False
                break
        self.filter_table()

    def _remove_party_by_id(self, party_id: int):
        """Remove party from in-memory lists and refresh table (kept for compatibility)."""
        self._deactivate_party_by_id(party_id)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Liabilities Management")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Refresh Button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setMinimumHeight(40)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #107c10, stop:1 #0d5f0d);
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                color: white;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1a9a1a, stop:1 #0d6f0d);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0d5f0d, stop:1 #0a4f0a);
            }
        """)
        refresh_btn.clicked.connect(self.refresh_parties)
        header_layout.addWidget(refresh_btn)
        
        # Add Liability Button
        add_btn = QPushButton("➕ Add Liability")
        add_btn.setMinimumHeight(40)
        add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0078d4, stop:1 #005a9e);
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                color: white;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1084e4, stop:1 #006aae);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #005a9e, stop:1 #004080);
            }
        """)
        add_btn.clicked.connect(self.add_party)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        # Search Bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        
        search_label = QLabel("🔍 Search:")
        search_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by liability name...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2a2a2a;
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        self.search_input.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.search_input)
        
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        clear_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_btn)
        
        layout.addLayout(search_layout)
        
        # Status label
        self.status_label = QLabel("Connecting to server...")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 12px;
                padding: 5px;
                background: rgba(45, 45, 45, 0.5);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Store original parties for filtering
        self.all_parties = []
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "15 Yards Rate", "22 Yards Rate", "Discount %", "Changelog"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                gridline-color: #3d3d3d;
                color: #ffffff;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QHeaderView::section {
                background-color: #1f1f1f;
                color: #ffffff;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #3d3d3d;
                font-weight: 600;
            }
        """)
        self.table.cellDoubleClicked.connect(self.edit_party)
        layout.addWidget(self.table)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        edit_btn = QPushButton("✏️ Edit")
        edit_btn.setMinimumHeight(35)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 20px;
                color: #ffffff;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        edit_btn.clicked.connect(self.edit_selected_party)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.setMinimumHeight(35)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d83b01;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e84b11;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected_party)
        btn_layout.addWidget(delete_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def load_parties_async(self):
        """Load parties asynchronously in background thread"""
        self.update_status_label("Connecting to server...", False)
        
        # Create and start background thread with API client (connection pooling)
        self.load_thread = PartyLoadThread(self.api_client)
        self.load_thread.finished.connect(self.on_parties_loaded)
        self.load_thread.start()
    
    def on_parties_loaded(self, parties, server_available):
        """Callback when parties are loaded in background thread"""
        self.parties = parties
        self.server_available = server_available
        
        if server_available:
            if parties:
                self.update_status_label("Connected", True)
            else:
                self.update_status_label("Connected - No parties found", True)
        else:
            self.update_status_label("Server offline - Data not available", False)
        
        self.populate_table()
    
    def refresh_parties(self):
        """Refresh parties data from database"""
        self.update_status_label("Refreshing data...", False)
        self.load_parties_async()
    
    def load_parties(self, silent=False):
        """Load parties from API using connection pooling (synchronous, for refresh operations)"""
        try:
            result = self.api_client.get_parties()
            
            if result and result.get("success"):
                self.parties = result.get("parties", [])
                self.server_available = True
                if self.parties:
                    self.update_status_label("Connected", True)
                else:
                    self.update_status_label("Connected - No parties found", True)
                self.populate_table()
            else:
                # Server not available
                self.parties = []
                self.server_available = False
                self.update_status_label("Server offline - Data not available", False)
                self.populate_table()
                
                if not silent:
                    QMessageBox.information(
                        self, "Server Offline",
                        "Cannot connect to API server. The table will be empty until the server is available.\n\n"
                        "Please ensure the host application is running."
                    )
                
        except Exception as e:
            # Other errors - show empty table
            self.parties = []
            self.server_available = False
            self.update_status_label(f"Error: {str(e)[:50]}", False)
            self.populate_table()
            
            if not silent:
                QMessageBox.warning(self, "Error", f"Failed to load parties: {str(e)}")
    
    def update_status_label(self, message, is_connected):
        """Update status label"""
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(message)
            color = "#4caf50" if is_connected else "#f44336"
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-size: 12px;
                    padding: 5px;
                    background: rgba(45, 45, 45, 0.5);
                    border-radius: 4px;
                }}
            """)
    
    def populate_table(self):
        """Populate table with parties"""
        # Store all parties for filtering
        self.all_parties = self.parties
        self.filter_table()
    
    def filter_table(self):
        """Filter table based on search criteria"""
        # Safety check: ensure widgets still exist (widget may have been destroyed)
        if not hasattr(self, 'table') or self.table is None:
            return
        try:
            # Test if widget is still valid
            _ = self.table.objectName()
        except RuntimeError:
            # Widget was deleted
            return
        
        if not hasattr(self, 'all_parties') or not self.all_parties:
            return
        
        search_text = ""
        if hasattr(self, 'search_input') and self.search_input is not None:
            try:
                search_text = self.search_input.text().upper()
            except RuntimeError:
                search_text = ""
        
        filtered_parties = []
        for party in self.all_parties:
            # Check search text against party name
            matches_search = True
            if search_text:
                party_name = party.get('name', '').upper()
                matches_search = search_text in party_name
            
            if matches_search:
                filtered_parties.append(party)
        
        # Populate table with filtered parties
        try:
            from PyQt5.QtGui import QBrush, QColor
            self.table.setRowCount(len(filtered_parties))
            for row, party in enumerate(filtered_parties):
                is_inactive = not party.get('is_active', True)
                red_brush = QBrush(QColor(255, 100, 100)) if is_inactive else None
                for col, (key, fmt) in enumerate([
                    ('id', lambda p: str(p['id'])),
                    ('name', lambda p: p['name']),
                    ('rate_15_yards', lambda p: f"{p['rate_15_yards']:.2f}"),
                    ('rate_22_yards', lambda p: f"{p['rate_22_yards']:.2f}"),
                    ('discount_percent', lambda p: f"{p['discount_percent']:.2f}%"),
                ]):
                    item = QTableWidgetItem(fmt(party))
                    if red_brush:
                        item.setForeground(red_brush)
                    self.table.setItem(row, col, item)
                changelog_text = self.get_changelog_text(party['id'])
                changelog_item = QTableWidgetItem(changelog_text)
                if red_brush:
                    changelog_item.setForeground(red_brush)
                self.table.setItem(row, 5, changelog_item)
        except RuntimeError:
            # Widget was deleted during operation
            pass
    
    def clear_search(self):
        """Clear search filter"""
        self.search_input.clear()
        self.filter_table()
    
    def get_changelog_text(self, party_id):
        """Get changelog text for a liability (party backend)"""
        try:
            # Use APIClient if available, otherwise fallback to direct request
            if hasattr(self, 'api_client') and self.api_client:
                result = self.api_client.get_party_changelog(party_id)
                if result and result.get("success"):
                    changelog = result.get("changelog", [])
                    if changelog:
                        # Show latest 3 entries
                        latest = changelog[:3]
                        texts = []
                        for entry in latest:
                            date = entry['change_date'][:10] if entry['change_date'] else ""
                            texts.append(f"{date}: {entry['changes']}")
                        return " | ".join(texts)
            else:
                # Fallback to direct request (for backward compatibility)
                response = requests.get(f"{CLIENT_FALLBACK_SERVER}/api/parties/{party_id}/changelog", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        changelog = data.get("changelog", [])
                        if changelog:
                            # Show latest 3 entries
                            latest = changelog[:3]
                            texts = []
                            for entry in latest:
                                date = entry['change_date'][:10] if entry['change_date'] else ""
                                texts.append(f"{date}: {entry['changes']}")
                            return " | ".join(texts)
            return "No changes"
        except:
            return "No changes"
    
    def add_party(self):
        """Show add liability dialog (party backend)"""
        if not self.server_available:
            QMessageBox.warning(
                self, "Server Offline",
                "Cannot add liability. The server is not available.\n\n"
                "Please ensure the host application is running."
            )
            return
        
        dialog = PartyDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            saved = getattr(dialog, "saved_party", None)
            if isinstance(saved, dict) and saved.get("id"):
                self._upsert_party(saved)
            else:
                self.load_parties_async()
    
    def edit_party(self, row, col):
        """Edit liability on double click"""
        self.edit_selected_party()
    
    def edit_selected_party(self):
        """Edit selected liability"""
        if not self.server_available:
            QMessageBox.warning(
                self, "Server Offline",
                "Cannot edit liability. The server is not available.\n\n"
                "Please ensure the host application is running."
            )
            return
        
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a liability to edit")
            return
        
        party_id = int(self.table.item(row, 0).text())
        party = next((p for p in self.parties if p['id'] == party_id), None)
        
        if party:
            dialog = PartyDialog(self, party)
            if dialog.exec_() == QDialog.Accepted:
                saved = getattr(dialog, "saved_party", None)
                if isinstance(saved, dict) and saved.get("id"):
                    self._upsert_party(saved)
                else:
                    self.load_parties_async()
    
    def delete_selected_party(self):
        """Delete selected liability"""
        if not self.server_available:
            QMessageBox.warning(
                self, "Server Offline",
                "Cannot delete liability. The server is not available.\n\n"
                "Please ensure the host application is running."
            )
            return
        
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a liability to delete")
            return
        
        party_id = int(self.table.item(row, 0).text())
        party_name = self.table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete liability '{party_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                result = self.api_client.delete_party(party_id)
                if result and result.get("success"):
                    QMessageBox.information(self, "Success", "Liability marked as inactive")
                    # Soft delete: update party in list to is_active=False (shows in red)
                    for p in (self.parties or []):
                        if p.get('id') == party_id:
                            p['is_active'] = False
                            break
                    for p in (self.all_parties or []):
                        if p.get('id') == party_id:
                            p['is_active'] = False
                            break
                    self.filter_table()
                else:
                    # Show server's detail message (e.g. "Cannot delete - has Stock Ledger, etc.")
                    err_msg = (result or {}).get("detail", "Failed to delete liability")
                    if isinstance(err_msg, list):
                        err_msg = err_msg[0] if err_msg else "Failed to delete liability"
                    QMessageBox.warning(self, "Cannot Delete", str(err_msg))
            except Exception as e:
                # Include response body if it has a detail (e.g. from requests with 400/500)
                err_str = str(e)
                if hasattr(e, "response") and e.response is not None:
                    try:
                        body = e.response.json()
                        if body.get("detail"):
                            err_str = body["detail"] if isinstance(body["detail"], str) else str(body["detail"])
                    except Exception:
                        pass
                QMessageBox.critical(self, "Cannot Delete", f"Failed to delete liability:\n\n{err_str}")


class PartyDialog(QDialog):
    """Dialog for adding/editing liability (party backend)"""
    
    def __init__(self, parent=None, party=None):
        super().__init__(parent)
        self.party = party
        self.saved_party = None  # returned by server for instant UI patching
        self.setWindowTitle("Edit Liability" if party else "Add Liability")
        self.setMinimumWidth(400)
        self.setStyleSheet(DARK_THEME)
        self.init_ui()
    
    def init_ui(self):
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        self.name_input.textChanged.connect(self.auto_uppercase_text)
        layout.addRow("Name:", self.name_input)
        
        # 15 Yards Rate
        self.rate_15_input = QDoubleSpinBox()
        self.rate_15_input.setMaximum(999999.99)
        self.rate_15_input.setDecimals(2)
        self.rate_15_input.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                font-size: 12px;
            }
            QDoubleSpinBox:focus {
                border: 2px solid #0078d4;
            }
        """)
        layout.addRow("15 Yards Rate:", self.rate_15_input)
        
        # 22 Yards Rate
        self.rate_22_input = QDoubleSpinBox()
        self.rate_22_input.setMaximum(999999.99)
        self.rate_22_input.setDecimals(2)
        self.rate_22_input.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                font-size: 12px;
            }
            QDoubleSpinBox:focus {
                border: 2px solid #0078d4;
            }
        """)
        layout.addRow("22 Yards Rate:", self.rate_22_input)
        
        # Discount Percent
        self.discount_input = QDoubleSpinBox()
        self.discount_input.setMaximum(100.00)
        self.discount_input.setDecimals(2)
        self.discount_input.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                font-size: 12px;
            }
            QDoubleSpinBox:focus {
                border: 2px solid #0078d4;
            }
        """)
        layout.addRow("Discount %:", self.discount_input)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_party)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        layout.addRow(buttons)
        
        self.setLayout(layout)
        
        # Populate if editing
        if self.party:
            self.name_input.setText(self.party['name'])
            self.rate_15_input.setValue(self.party['rate_15_yards'])
            self.rate_22_input.setValue(self.party['rate_22_yards'])
            self.discount_input.setValue(self.party['discount_percent'])
    
    def auto_uppercase_text(self, text):
        """Automatically convert text to uppercase as user types"""
        sender = self.sender()
        if sender:
            cursor_pos = sender.cursorPosition()
            uppercase_text = text.upper()
            if text != uppercase_text:
                sender.blockSignals(True)
                sender.setText(uppercase_text)
                sender.setCursorPosition(min(cursor_pos, len(uppercase_text)))
                sender.blockSignals(False)
    
    def save_party(self):
        """Save liability using connection pooling (party backend)"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Name is required")
            return
        
        try:
            # Get API client from parent (PartyModule)
            api_client = self.parent().api_client if hasattr(self.parent(), 'api_client') else None
            if not api_client:
                # Fallback: create new client if parent doesn't have one
                from client.api_client import APIClient
                api_client = APIClient()
            
            if self.party:
                # Update using connection pooling
                result = api_client.update_party(
                    self.party['id'],
                    name,
                    self.rate_15_input.value(),
                    self.rate_22_input.value(),
                    self.discount_input.value()
                )
            else:
                # Create using connection pooling
                result = api_client.create_party(
                    name,
                    self.rate_15_input.value(),
                    self.rate_22_input.value(),
                    self.discount_input.value()
                )
            
            if result and result.get("success"):
                QMessageBox.information(self, "Success", result.get("message", "Liability saved successfully"))
                if isinstance(result.get("party"), dict):
                    self.saved_party = result.get("party")
                self.accept()
            else:
                if result:
                    error_msg = result.get("message", "Failed to save party")
                    if result.get("detail"):
                        error_msg = result.get("detail")
                else:
                    error_msg = "Connection error: Unable to connect to the server. Please ensure the API server is running."
                QMessageBox.warning(self, "Error", error_msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save party: {str(e)}")


class NameOnlyMasterModule(QWidget):
    """
    Generic name-only master module used for:
    - Assets
    - Expenses
    - Vendors

    Accounting behaviour:
    - Master data only
    - No balances, quantities, or transactional logic
    """

    def __init__(self, title_text: str, entity_label: str, fetch_fn, create_fn, update_fn, deactivate_fn, user_data=None):
        super().__init__()
        self.module_title = title_text
        self.entity_label = entity_label  # e.g. "Asset", "Expense", "Vendor"
        self.fetch_fn = fetch_fn
        self.create_fn = create_fn
        self.update_fn = update_fn
        self.deactivate_fn = deactivate_fn
        self.user_data = user_data

        from client.api_client import APIClient
        username = (user_data or {}).get("username")
        self.api_client = APIClient(username=username)

        self.records = []
        self.server_available = False

        self.init_ui()
        self.load_records()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel(self.module_title)
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Refresh Button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setMinimumHeight(40)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #107c10, stop:1 #0d5f0d);
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                color: white;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a9a1a, stop:1 #0d6f0d);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0d5f0d, stop:1 #0a4f0a);
            }
        """)
        refresh_btn.clicked.connect(self.load_records)
        header_layout.addWidget(refresh_btn)

        # Add Button
        add_btn = QPushButton(f"➕ Add {self.entity_label}")
        add_btn.setMinimumHeight(40)
        add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                color: white;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1084e4, stop:1 #006aae);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #005a9e, stop:1 #004080);
            }
        """)
        add_btn.clicked.connect(self.add_record)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Search Bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)

        search_label = QLabel("🔍 Search:")
        search_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(f"Search by {self.entity_label.lower()} name...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2a2a2a;
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        self.search_input.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.search_input)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        clear_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_btn)

        layout.addLayout(search_layout)

        # Status label
        self.status_label = QLabel("Connecting to server...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 12px;
                padding: 5px;
                background: rgba(45, 45, 45, 0.5);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.status_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Name",
            "Status",
            "Change Log (Created / Last Modified / User)"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                gridline-color: #3d3d3d;
                color: #ffffff;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QHeaderView::section {
                background-color: #1f1f1f;
                color: #ffffff;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #3d3d3d;
                font-weight: 600;
            }
        """)
        self.table.cellDoubleClicked.connect(self.edit_record)
        layout.addWidget(self.table)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        edit_btn = QPushButton("✏️ Edit")
        edit_btn.setMinimumHeight(35)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 20px;
                color: #ffffff;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        edit_btn.clicked.connect(self.edit_selected_record)
        btn_layout.addWidget(edit_btn)

        deactivate_btn = QPushButton("🚫 Deactivate")
        deactivate_btn.setMinimumHeight(35)
        deactivate_btn.setStyleSheet("""
            QPushButton {
                background-color: #d83b01;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e84b11;
            }
        """)
        deactivate_btn.clicked.connect(self.deactivate_selected_record)
        btn_layout.addWidget(deactivate_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def update_status_label(self, message: str, is_connected: bool):
        """Update status label based on connectivity."""
        self.status_label.setText(message)
        color = "#4caf50" if is_connected else "#f44336"
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 12px;
                padding: 5px;
                background: rgba(45, 45, 45, 0.5);
                border-radius: 4px;
            }}
        """)

    def load_records(self):
        """Load name-only master records from the API."""
        try:
            result = self.fetch_fn(self.api_client)
            key = None
            if isinstance(result, dict):
                # Detect list key (assets / expenses / vendors)
                for candidate in ("assets", "expenses", "vendors"):
                    if candidate in result:
                        key = candidate
                        break
            if not result or not key:
                self.records = []
                self.server_available = False
                self.update_status_label("Server offline - Data not available", False)
            else:
                self.records = result.get(key, [])
                self.server_available = True
                if self.records:
                    self.update_status_label("Connected", True)
                else:
                    self.update_status_label("Connected - No records found", True)
            self.populate_table()
        except Exception as e:
            self.records = []
            self.server_available = False
            self.update_status_label(f"Error: {str(e)[:50]}", False)
            self.populate_table()

    def populate_table(self):
        """Populate grid with filtered records."""
        self.filter_table()

    def format_changelog(self, record: dict) -> str:
        """Build Change Log text from audit fields."""
        created_at = (record.get("created_at") or "")[:10]
        updated_at = (record.get("updated_at") or "")[:10]
        created_by = record.get("created_by") or ""
        updated_by = record.get("updated_by") or ""

        created_part = f"Created: {created_at}" if created_at else "Created: -"
        if created_by:
            created_part += f" by {created_by}"

        updated_part = "Last modified: -"
        if updated_at:
            updated_part = f"Last modified: {updated_at}"
            if updated_by:
                updated_part += f" by {updated_by}"

        return f"{created_part} | {updated_part}"

    def filter_table(self):
        """Filter records by name."""
        search_text = (self.search_input.text() or "").upper()

        filtered = []
        for rec in self.records or []:
            name = (rec.get("name") or "").upper()
            if not search_text or search_text in name:
                filtered.append(rec)

        self.table.setRowCount(len(filtered))
        for row, rec in enumerate(filtered):
            self.table.setItem(row, 0, QTableWidgetItem(str(rec.get("id", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(rec.get("name", "")))
            status = "Active" if rec.get("is_active", True) else "Inactive"
            status_item = QTableWidgetItem(status)
            if status == "Inactive":
                status_item.setForeground(Qt.red)
            self.table.setItem(row, 2, status_item)
            self.table.setItem(row, 3, QTableWidgetItem(self.format_changelog(rec)))

    def clear_search(self):
        self.search_input.clear()
        self.filter_table()

    def _get_selected_record(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        record_id_item = self.table.item(row, 0)
        if not record_id_item:
            return None
        try:
            record_id = int(record_id_item.text())
        except ValueError:
            return None
        for rec in self.records or []:
            if rec.get("id") == record_id:
                return rec
        return None

    def add_record(self):
        """Add a new master name."""
        if not self.server_available:
            QMessageBox.warning(
                self,
                "Server Offline",
                f"Cannot add {self.entity_label.lower()}. The server is not available.\n\n"
                "Please ensure the host application is running.",
            )
            return

        name, ok = self._prompt_for_name(f"Add {self.entity_label}", "")
        if not ok or not name:
            return

        try:
            result = self.create_fn(self.api_client, name)
            if result and result.get("success"):
                QMessageBox.information(self, "Success", f"{self.entity_label} created successfully")
                self.load_records()
            else:
                message = (result or {}).get("message", f"Failed to create {self.entity_label.lower()}")
                QMessageBox.warning(self, "Error", message)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create {self.entity_label.lower()}: {str(e)}")

    def edit_record(self, row: int, col: int):
        """Edit record on double click."""
        self.edit_selected_record()

    def edit_selected_record(self):
        """Edit currently selected master name."""
        if not self.server_available:
            QMessageBox.warning(
                self,
                "Server Offline",
                f"Cannot edit {self.entity_label.lower()}. The server is not available.\n\n"
                "Please ensure the host application is running.",
            )
            return

        rec = self._get_selected_record()
        if not rec:
            QMessageBox.warning(self, "No Selection", f"Please select a {self.entity_label.lower()} to edit")
            return

        name, ok = self._prompt_for_name(f"Edit {self.entity_label}", rec.get("name", ""))
        if not ok or not name:
            return

        try:
            result = self.update_fn(self.api_client, rec.get("id"), name)
            if result and result.get("success"):
                QMessageBox.information(self, "Success", f"{self.entity_label} updated successfully")
                self.load_records()
            else:
                message = (result or {}).get("message", f"Failed to update {self.entity_label.lower()}")
                QMessageBox.warning(self, "Error", message)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update {self.entity_label.lower()}: {str(e)}")

    def deactivate_selected_record(self):
        """Deactivate the selected master name."""
        if not self.server_available:
            QMessageBox.warning(
                self,
                "Server Offline",
                f"Cannot deactivate {self.entity_label.lower()}. The server is not available.\n\n"
                "Please ensure the host application is running.",
            )
            return

        rec = self._get_selected_record()
        if not rec:
            QMessageBox.warning(self, "No Selection", f"Please select a {self.entity_label.lower()} to deactivate")
            return

        if not rec.get("is_active", True):
            QMessageBox.information(self, "Already Inactive", f"The selected {self.entity_label.lower()} is already inactive.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Deactivation",
            f"Are you sure you want to deactivate this {self.entity_label.lower()}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            result = self.deactivate_fn(self.api_client, rec.get("id"))
            if result and result.get("success"):
                QMessageBox.information(self, "Success", f"{self.entity_label} deactivated successfully")
                self.load_records()
            else:
                message = (result or {}).get("message", f"Failed to deactivate {self.entity_label.lower()}")
                QMessageBox.warning(self, "Error", message)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to deactivate {self.entity_label.lower()}: {str(e)}")

    def _prompt_for_name(self, title: str, initial: str):
        """Prompt the user for a master name (simple line edit dialog)."""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setStyleSheet(DARK_THEME)

        form = QFormLayout(dialog)
        form.setSpacing(15)
        form.setContentsMargins(20, 20, 20, 20)

        name_edit = QLineEdit()
        name_edit.setText(initial)
        name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
            }
        """)

        def auto_upper(text: str):
            cursor_pos = name_edit.cursorPosition()
            upper = text.upper()
            if text != upper:
                name_edit.blockSignals(True)
                name_edit.setText(upper)
                name_edit.setCursorPosition(min(cursor_pos, len(upper)))
                name_edit.blockSignals(False)

        name_edit.textChanged.connect(auto_upper)
        form.addRow("Name:", name_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec_() == QDialog.Accepted:
            name = name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "Validation", "Name is required")
                return "", False
            return name, True
        return "", False


class DefineWindow(QMainWindow):
    """Define Window with ESC key navigation"""
    
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
        self.setWindowTitle("TMS - Define")
        self.setMinimumSize(1200, 700)
        self.setStyleSheet(DARK_THEME)
        
        # Set window to full screen (covers entire screen including taskbar)
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
        
        # Check user permissions
        user_modules = self.user_data.get("modules", []) if self.user_data else []
        is_admin = self.user_data.get("role") == "ADMIN" if self.user_data else False
        
        # Sidebar (created before modules to check permissions)
        self.sidebar = AnimatedSidebar(central_widget)

        # Liabilities module (index 1) - renamed from Party
        if is_admin or "define.party" in user_modules or "define.liabilities" in user_modules or "define" in user_modules:
            self.stacked_widget.addWidget(PartyModule(user_data=self.user_data))
            self.sidebar.party_btn.clicked.connect(lambda: self.show_module(1))
        else:
            # User doesn't have access to liabilities module
            self.sidebar.party_btn.setVisible(False)

        # Assets module (index 2)
        from client.api_client import APIClient  # local import to avoid cycles at top

        def _fetch_assets(api_client: APIClient):
            return api_client.get_assets()

        def _create_asset(api_client: APIClient, name: str):
            return api_client.create_asset(name)

        def _update_asset(api_client: APIClient, rec_id: int, name: str):
            return api_client.update_asset(rec_id, name)

        def _deactivate_asset(api_client: APIClient, rec_id: int):
            return api_client.deactivate_asset(rec_id)

        # Next available stacked widget index after welcome and liabilities (if present)
        next_index = self.stacked_widget.count()

        if is_admin or "define.assets" in user_modules or "define" in user_modules:
            assets_module = NameOnlyMasterModule(
                title_text="Assets Master",
                entity_label="Asset",
                fetch_fn=_fetch_assets,
                create_fn=_create_asset,
                update_fn=_update_asset,
                deactivate_fn=_deactivate_asset,
                user_data=self.user_data,
            )
            self.stacked_widget.addWidget(assets_module)

            # Add sidebar button for Assets
            assets_btn = QPushButton("🏦 Assets")
            assets_btn.setMinimumHeight(50)
            assets_btn.setStyleSheet(self.sidebar.party_btn.styleSheet())
            self.sidebar.layout().insertWidget(self.sidebar.layout().count() - 1, assets_btn)
            assets_btn.clicked.connect(lambda _checked=False, idx=next_index: self.show_module(idx))
            next_index += 1

        # Expenses module
        def _fetch_expenses(api_client: APIClient):
            return api_client.get_expenses()

        def _create_expense(api_client: APIClient, name: str):
            return api_client.create_expense(name)

        def _update_expense(api_client: APIClient, rec_id: int, name: str):
            return api_client.update_expense(rec_id, name)

        def _deactivate_expense(api_client: APIClient, rec_id: int):
            return api_client.deactivate_expense(rec_id)

        if is_admin or "define.expenses" in user_modules or "define" in user_modules:
            expenses_module = NameOnlyMasterModule(
                title_text="Expenses Master",
                entity_label="Expense",
                fetch_fn=_fetch_expenses,
                create_fn=_create_expense,
                update_fn=_update_expense,
                deactivate_fn=_deactivate_expense,
                user_data=self.user_data,
            )
            self.stacked_widget.addWidget(expenses_module)

            expenses_btn = QPushButton("💸 Expenses")
            expenses_btn.setMinimumHeight(50)
            expenses_btn.setStyleSheet(self.sidebar.party_btn.styleSheet())
            self.sidebar.layout().insertWidget(self.sidebar.layout().count() - 1, expenses_btn)
            expenses_btn.clicked.connect(lambda _checked=False, idx=next_index: self.show_module(idx))
            next_index += 1

        # Vendors module
        def _fetch_vendors(api_client: APIClient):
            return api_client.get_vendors()

        def _create_vendor(api_client: APIClient, name: str):
            return api_client.create_vendor(name)

        def _update_vendor(api_client: APIClient, rec_id: int, name: str):
            return api_client.update_vendor(rec_id, name)

        def _deactivate_vendor(api_client: APIClient, rec_id: int):
            return api_client.deactivate_vendor(rec_id)

        if is_admin or "define.vendors" in user_modules or "define" in user_modules:
            vendors_module = NameOnlyMasterModule(
                title_text="Vendors Master",
                entity_label="Vendor",
                fetch_fn=_fetch_vendors,
                create_fn=_create_vendor,
                update_fn=_update_vendor,
                deactivate_fn=_deactivate_vendor,
                user_data=self.user_data,
            )
            self.stacked_widget.addWidget(vendors_module)

            vendors_btn = QPushButton("📂 Vendors")
            vendors_btn.setMinimumHeight(50)
            vendors_btn.setStyleSheet(self.sidebar.party_btn.styleSheet())
            self.sidebar.layout().insertWidget(self.sidebar.layout().count() - 1, vendors_btn)
            vendors_btn.clicked.connect(lambda _checked=False, idx=next_index: self.show_module(idx))
        
        # Add stacked widget to layout
        main_layout.addWidget(self.stacked_widget)
        
        central_widget.setLayout(main_layout)
        self.sidebar.setParent(central_widget)  # Ensure proper parent
        self.sidebar.raise_()  # Ensure sidebar is on top layer
        
        # Install event filter for ESC key
        self.installEventFilter(self)
    
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
    
    def show_module(self, index):
        """Show module by index"""
        # Remove blur if exists
        if self.blur_effect:
            current_widget = self.stacked_widget.currentWidget()
            if current_widget:
                current_widget.setGraphicsEffect(None)
            self.blur_effect = None
        
        # Hide sidebar
        if self.sidebar.is_visible:
            self.sidebar.hide_sidebar()
        
        # Show module
        if 0 <= index < self.stacked_widget.count():
            self.stacked_widget.setCurrentIndex(index)
            # Ensure the stacked widget is visible
            self.stacked_widget.show()
            self.stacked_widget.raise_()
    
    def eventFilter(self, obj, event):
        """Handle ESC key events and F11 to toggle full screen"""
        if event.type() == QKeyEvent.KeyPress:
            if event.key() == Qt.Key_F11:
                # F11: Toggle full screen mode
                if self.isFullScreen():
                    self.showNormal()
                else:
                    self.showFullScreen()
                return True
            elif event.key() == Qt.Key_Escape:
                current_time = int(time.time() * 1000)  # milliseconds
                
                # Check for double ESC
                if self.esc_press_time > 0:
                    time_diff = abs(current_time - self.esc_press_time)
                    if time_diff < self.esc_double_click_threshold:
                        # Double ESC - exit to main window
                        self.return_to_main()
                        self.esc_press_time = 0
                        return True
                
                self.esc_press_time = current_time
                
                # Single ESC - toggle sidebar
                current_index = self.stacked_widget.currentIndex()
                
                if not self.sidebar.is_visible:
                    # Sidebar hidden - show it and blur content
                    self.sidebar.show_sidebar()
                    # Add blur to current widget
                    current_widget = self.stacked_widget.currentWidget()
                    if current_widget:
                        self.blur_effect = QGraphicsBlurEffect()
                        self.blur_effect.setBlurRadius(10)
                        current_widget.setGraphicsEffect(self.blur_effect)
                else:
                    # Sidebar visible - hide it and remove blur
                    self.sidebar.hide_sidebar()
                    # Remove blur
                    if self.blur_effect:
                        current_widget = self.stacked_widget.currentWidget()
                        if current_widget:
                            current_widget.setGraphicsEffect(None)
                        self.blur_effect = None
                
                return True
        
        return super().eventFilter(obj, event)
    
    def return_to_main(self):
        """Return to main application window"""
        main_window = getattr(self, 'main_window', self.parent_window)
        if main_window:
            # Save current window state
            main_window.window_state_before_hide = self.windowState()
            main_window.window_geometry_before_hide = self.geometry()
            
            main_window.show()
            main_window.raise_()
            main_window.activateWindow()
            self.hide()
    
    def showEvent(self, event):
        """Restore window state when shown"""
        super().showEvent(event)
        if not self.isMinimized():
            self.showFullScreen()

