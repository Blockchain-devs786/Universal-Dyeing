"""Transfer, Outward, and Stock Modules - Continuation of data_entry_modules.py"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QLineEdit, QFormLayout,
    QDialogButtonBox, QMessageBox, QComboBox, QDoubleSpinBox, QDateEdit,
    QAbstractItemView, QListWidget, QListWidgetItem, QCompleter, QCheckBox
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal, QStringListModel, QUrl
from PyQt5.QtGui import QFont, QDesktopServices
import requests
import os
import tempfile
import webbrowser
import base64
from datetime import datetime
from common.config import CLIENT_FALLBACK_SERVER
from client.api_client import APIClient


# ==================== TRANSFER TYPE SELECTION DIALOG ====================

class TransferTypeDialog(QDialog):
    """Dialog for selecting transfer type (Simple or By Name)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_type = None
        self.setWindowTitle("Select Transfer Type")
        self.setMinimumSize(400, 200)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        label = QLabel("Select Transfer Type:")
        label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        layout.addWidget(label)
        
        # Simple Transfer Button
        simple_btn = QPushButton("📦 Simple Transfer")
        simple_btn.setMinimumHeight(50)
        simple_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 8px;
                padding: 15px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        simple_btn.clicked.connect(lambda: self.select_type('simple'))
        layout.addWidget(simple_btn)
        
        # By Name Transfer Button
        by_name_btn = QPushButton("🏷️ By Name Transfer")
        by_name_btn.setMinimumHeight(50)
        by_name_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                border: none;
                border-radius: 8px;
                padding: 15px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        by_name_btn.clicked.connect(lambda: self.select_type('by_name'))
        layout.addWidget(by_name_btn)
        
        # Cancel Button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
                border-radius: 6px;
                padding: 10px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        self.setLayout(layout)
    
    def select_type(self, transfer_type):
        """Select transfer type and close dialog"""
        self.selected_type = transfer_type
        self.accept()


# ==================== PARTY SEARCH DIALOG ====================

class PartySearchDialog(QDialog):
    """Dialog for searching and selecting MS Party"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_party = None
        self.api_client = APIClient()  # Initialize API client
        self.setWindowTitle("Select MS Party")
        self.setMinimumSize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        self.init_ui()
        self.load_parties()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Search label
        search_label = QLabel("Search MS Party:")
        search_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(search_label)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 10px;
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        self.search_input.textChanged.connect(self.filter_parties)
        layout.addWidget(self.search_input)
        
        # Party list
        self.party_list = QListWidget()
        self.party_list.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                color: #ffffff;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #3d3d3d;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        self.party_list.itemDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.party_list)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_selection)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def load_parties(self):
        """Load parties with available stock"""
        if not hasattr(self, 'api_client') or self.api_client is None:
            self.api_client = APIClient()
        try:
            response = self.api_client._try_request("GET", "/api/stock/parties")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.all_parties = data.get("parties", [])
                    self.filter_parties()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load parties: {str(e)}")
            self.all_parties = []
    
    def filter_parties(self):
        """Filter parties based on search text"""
        if not hasattr(self, 'all_parties'):
            self.all_parties = []
        if not hasattr(self, 'search_input') or not hasattr(self, 'party_list'):
            return
        
        search_text = self.search_input.text().lower()
        self.party_list.clear()
        
        for party in self.all_parties:
            party_name = party.get('name', '')
            if search_text in party_name.lower():
                item = QListWidgetItem(party_name)
                item.setData(Qt.UserRole, party)
                self.party_list.addItem(item)
    
    def accept_selection(self):
        """Accept the selected party"""
        current_item = self.party_list.currentItem()
        if current_item:
            self.selected_party = current_item.data(Qt.UserRole)
            self.accept()
        else:
            QMessageBox.warning(self, "Selection Required", "Please select an MS Party")

# Import DocumentLoader from data_entry_modules (defined there to avoid circular import)
# Use a delayed import to avoid circular dependency
def get_document_loader():
    """Get DocumentLoader class - delayed import to avoid circular dependency"""
    from common.ui.data_entry_modules import DocumentLoader
    return DocumentLoader

# For now, we'll define it here too to avoid the circular import
class DocumentLoader(QThread):
    """Thread for loading documents"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, doc_type, transfer_type=None):
        super().__init__()
        self.doc_type = doc_type
        self.transfer_type = transfer_type  # 'simple' or 'by_name' for transfers
        self.api_client = APIClient()
    
    def run(self):
        try:
            endpoint = f"/api/{self.doc_type}"
            # Add transfer_type parameter if it's a transfer request
            params = None
            if self.doc_type == "transfer" and self.transfer_type:
                params = {"transfer_type": self.transfer_type}
            
            response = self.api_client._try_request("GET", endpoint, params=params)
            if response:
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        self.finished.emit(data.get("documents", []))
                    else:
                        self.error.emit(data.get("message", "Unknown error"))
                else:
                    self.error.emit(f"Server returned status {response.status_code}")
            else:
                self.error.emit("Connection error: Unable to reach server")
        except Exception as e:
            self.error.emit(str(e))


# ==================== TRANSFER MODULE ====================

class TransferModule(QWidget):
    """Transfer Data Entry Module with Simple and By Name Transfer filtering"""
    
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data
        self.server_available = True
        self.ws_bus = (user_data or {}).get("ws_bus")
        self.api_client = APIClient()
        # Set username on API client for edited_by tracking
        if user_data and user_data.get('username'):
            self.api_client.set_username(user_data.get('username'))
        self._data_loaded = False  # Track if data has been loaded
        self._setup_realtime("transfer")
        self.init_ui()
        # Don't load data immediately - wait until module is shown
        self.transfer_type_filter = 'simple'  # Filter for print dialog
    
    def load_data_if_needed(self):
        """Load data if not already loaded (called explicitly when module is shown)"""
        if not self._data_loaded:
            self._data_loaded = True
            self.load_documents_async()
    
    def showEvent(self, event):
        """Handle show event (but don't load here - use load_data_if_needed instead)"""
        super().showEvent(event)

    def _setup_realtime(self, entity: str):
        """Wire up WebSocket → Qt bus for real-time UI patching."""
        self.realtime_entity = entity
        if self.ws_bus:
            try:
                self.ws_bus.message.connect(self.on_realtime_message)
            except Exception:
                pass

    def on_realtime_message(self, message: dict):
        """Apply server-pushed CRUD updates (so client UIs update instantly)."""
        if not isinstance(message, dict):
            return
        if message.get("type") != "entity_change":
            return
        if message.get("entity") != getattr(self, "realtime_entity", None):
            return

        action = message.get("action")
        data = message.get("data") or {}
        if action in ("created", "updated"):
            if isinstance(data, dict) and data.get("id"):
                self._upsert_document(data, prefer_top=(action == "created"))
        elif action == "deleted":
            doc_id = data.get("id") if isinstance(data, dict) else None
            if doc_id:
                self._remove_document_by_id(doc_id)

    def _upsert_document(self, doc: dict, prefer_top: bool = False):
        """Insert or update a document in-memory and refresh table view."""
        # Safety check: ensure widget still exists
        if not hasattr(self, 'table') or self.table is None:
            return
        try:
            _ = self.table.objectName()
        except RuntimeError:
            # Widget was deleted, ignore update
            return
        
        if not hasattr(self, "all_documents") or self.all_documents is None:
            self.all_documents = []

        doc_id = doc.get("id")
        if not doc_id:
            return

        existing_idx = next((i for i, d in enumerate(self.all_documents) if d.get("id") == doc_id), None)
        if existing_idx is None:
            if prefer_top:
                self.all_documents.insert(0, doc)
            else:
                self.all_documents.append(doc)
        else:
            self.all_documents[existing_idx] = doc

        self.filter_table()

    def _remove_document_by_id(self, doc_id: int):
        """Remove a document from in-memory list and refresh table view."""
        # Safety check: ensure widget still exists
        if not hasattr(self, 'table') or self.table is None:
            return
        try:
            _ = self.table.objectName()
        except RuntimeError:
            # Widget was deleted, ignore update
            return
        
        if not hasattr(self, "all_documents"):
            self.all_documents = []
        
        # Remove the document from the list
        self.all_documents = [d for d in self.all_documents if d.get("id") != doc_id]
        
        # Always refresh the table, even if all_documents is now empty
        self.filter_table()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("🔄 Transfer Documents")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)
        header.addStretch()
        
        self.add_btn = QPushButton("➕ Add Transfer")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.add_btn.clicked.connect(self.add_transfer)
        header.addWidget(self.add_btn)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        self.refresh_btn.clicked.connect(self.load_documents_async)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # Filter Bar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        # MS Party Filter
        ms_party_label = QLabel("MS Party:")
        ms_party_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        filter_layout.addWidget(ms_party_label)
        
        self.ms_party_filter = QLineEdit()
        self.ms_party_filter.setPlaceholderText("Filter by MS Party...")
        self.ms_party_filter.setStyleSheet("""
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
        self.ms_party_filter.textChanged.connect(self.filter_table)
        filter_layout.addWidget(self.ms_party_filter)
        
        # GP # Filter
        gp_label = QLabel("GP #:")
        gp_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        filter_layout.addWidget(gp_label)
        
        self.gp_filter = QLineEdit()
        self.gp_filter.setPlaceholderText("Filter by GP #...")
        self.gp_filter.setStyleSheet("""
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
        self.gp_filter.textChanged.connect(self.filter_table)
        self.gp_filter.textChanged.connect(self.auto_uppercase_text)
        filter_layout.addWidget(self.gp_filter)
        
        # TRANSFER # Filter
        transfer_label = QLabel("TRANSFER #:")
        transfer_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        filter_layout.addWidget(transfer_label)
        
        self.transfer_filter = QLineEdit()
        self.transfer_filter.setPlaceholderText("Filter by TRANSFER #...")
        self.transfer_filter.setStyleSheet("""
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
        self.transfer_filter.textChanged.connect(self.filter_table)
        self.transfer_filter.textChanged.connect(self.auto_uppercase_text)
        filter_layout.addWidget(self.transfer_filter)
        
        # Date range filters
        date_label = QLabel("From:")
        date_label.setStyleSheet("color: #ffffff;")
        filter_layout.addWidget(date_label)
        
        self.from_date_input = QDateEdit()
        self.from_date_input.setDate(QDate(2000, 1, 1))
        self.from_date_input.setCalendarPopup(True)
        self.from_date_input.setStyleSheet("""
            QDateEdit {
                background-color: #2a2a2a;
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
            }
            QDateEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        self.from_date_input.dateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.from_date_input)
        
        to_label = QLabel("To:")
        to_label.setStyleSheet("color: #ffffff;")
        filter_layout.addWidget(to_label)
        
        self.to_date_input = QDateEdit()
        self.to_date_input.setDate(QDate(2099, 12, 31))
        self.to_date_input.setCalendarPopup(True)
        self.to_date_input.setStyleSheet("""
            QDateEdit {
                background-color: #2a2a2a;
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
            }
            QDateEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        self.to_date_input.dateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.to_date_input)
        
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
        filter_layout.addWidget(clear_btn)
        
        layout.addLayout(filter_layout)
        
        # Setup autocomplete for MS Party filter
        self.setup_ms_party_autocomplete()
        
        # Store original documents for filtering
        self.all_documents = []
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "TRANSFER #", "GP #", "SR #", "MS Party", "From Party",
            "Transfer To", "Vehicle #", "Driver", "Total Qty", "Date"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #252525;
                border: 1px solid #3d3d3d;
                gridline-color: #3d3d3d;
                color: #ffffff;
            }
            QTableWidget::item {
                padding: 5px;
                background-color: #1e1e1e;
            }
            QTableWidget::item:alternate {
                background-color: #252525;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QTableWidget::item:selected:alternate {
                background-color: #0078d4;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                padding: 8px;
                border: none;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.edit_selected_transfer)
        # Set column widths - give more space to "Transfer To" column (index 5)
        self.table.setColumnWidth(5, 180)  # Transfer To column
        layout.addWidget(self.table)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.clicked.connect(self.edit_selected_transfer)
        self.edit_btn.setEnabled(False)
        action_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self.delete_selected_transfer)
        self.delete_btn.setEnabled(False)
        action_layout.addWidget(self.delete_btn)
        
        self.print_btn = QPushButton("🖨️ Print")
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #107c10;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0d5f0d;
            }
        """)
        self.print_btn.clicked.connect(self.print_transfers)
        action_layout.addWidget(self.print_btn)
        
        layout.addLayout(action_layout)
        
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        self.setLayout(layout)
    
    def on_selection_changed(self):
        has_selection = len(self.table.selectedItems()) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def load_documents_async(self):
        """Load all transfer documents (both simple and by_name)"""
        self.loader = DocumentLoader("transfer")  # Load all transfers (no type filter)
        self.loader.finished.connect(self.populate_table)
        self.loader.error.connect(self.on_load_error)
        self.loader.start()
    
    def populate_table(self, documents):
        """Populate table with documents"""
        # Store all documents for filtering
        self.all_documents = documents
        self.filter_table()
    
    def setup_ms_party_autocomplete(self):
        """Set up autocomplete for MS Party filter"""
        try:
            # Get MS parties only (from party management module)
            response = self.api_client._try_request("GET", "/api/parties")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    parties = data.get("parties", [])
                    active_parties = [p for p in parties if p.get('is_active', True)]
                    party_names = [party['name'] for party in active_parties]
                    
                    from PyQt5.QtWidgets import QCompleter
                    from PyQt5.QtCore import Qt
                    completer = QCompleter(party_names, self.ms_party_filter)
                    completer.setCaseSensitivity(Qt.CaseInsensitive)
                    completer.setCompletionMode(QCompleter.PopupCompletion)
                    completer.setFilterMode(Qt.MatchContains)
                    completer.setMaxVisibleItems(10)
                    self.ms_party_filter.setCompleter(completer)
                    
                    # Style the completer popup
                    completer.popup().setStyleSheet("""
                        QListView {
                            background-color: #1e1e1e;
                            border: 1px solid #3d3d3d;
                            color: #ffffff;
                            selection-background-color: #0078d4;
                            selection-color: #ffffff;
                            padding: 2px;
                        }
                    """)
        except:
            pass
    
    def auto_uppercase_text(self, text):
        """Automatically convert text to uppercase as user types (except MS Party filter)"""
        sender = self.sender()
        if sender and sender != self.ms_party_filter:  # Don't uppercase MS Party filter (for autocomplete)
            cursor_pos = sender.cursorPosition()
            uppercase_text = text.upper()
            if text != uppercase_text:
                sender.blockSignals(True)
                sender.setText(uppercase_text)
                sender.setCursorPosition(min(cursor_pos, len(uppercase_text)))
                sender.blockSignals(False)
    
    def filter_table(self):
        """Filter table based on search criteria"""
        # Safety check: ensure widget still exists
        if not hasattr(self, 'table') or self.table is None:
            return
        try:
            _ = self.table.objectName()
        except RuntimeError:
            # Widget was deleted
            return
        
        if not hasattr(self, 'all_documents'):
            self.all_documents = []
        
        # If all_documents is empty, clear the table
        if not self.all_documents:
            try:
                self.table.setRowCount(0)
            except RuntimeError:
                pass
            return
        
        # Get filter values
        ms_party_filter = ""
        gp_filter = ""
        transfer_filter = ""
        from_date = QDate(2000, 1, 1)
        to_date = QDate(2099, 12, 31)
        
        try:
            if hasattr(self, 'ms_party_filter') and self.ms_party_filter is not None:
                ms_party_filter = self.ms_party_filter.text().upper()
            if hasattr(self, 'gp_filter') and self.gp_filter is not None:
                gp_filter = self.gp_filter.text().upper()
            if hasattr(self, 'transfer_filter') and self.transfer_filter is not None:
                transfer_filter = self.transfer_filter.text().upper()
            if hasattr(self, 'from_date_input') and self.from_date_input is not None:
                from_date = self.from_date_input.date()
            if hasattr(self, 'to_date_input') and self.to_date_input is not None:
                to_date = self.to_date_input.date()
        except RuntimeError:
            # Widgets were deleted
            pass
        
        filtered_docs = []
        for doc in self.all_documents:
            # This main Transfer list is now dedicated to SIMPLE transfers only.
            # Skip any 'by_name' transfers so they appear only in the separate window.
            doc_transfer_type = doc.get('transfer_type', 'simple')
            if doc_transfer_type == 'by_name':
                continue
            # Check MS Party filter
            matches_ms_party = True
            if ms_party_filter:
                ms_party = doc.get('ms_party_name', '').upper()
                matches_ms_party = ms_party_filter in ms_party
            
            # Check GP # filter
            matches_gp = True
            if gp_filter:
                gp_num = doc.get('gp_number', '').upper()
                matches_gp = gp_filter in gp_num
            
            # Check TRANSFER # filter
            matches_transfer = True
            if transfer_filter:
                transfer_num = doc.get('transfer_number', '').upper()
                matches_transfer = transfer_filter in transfer_num
            
            # Check date range
            matches_date = True
            doc_date_str = doc.get('document_date', '')
            if doc_date_str:
                try:
                    doc_date = QDate.fromString(doc_date_str[:10], "yyyy-MM-dd")
                    matches_date = from_date <= doc_date <= to_date
                except:
                    matches_date = True
            
            # All filters must match (AND logic)
            if matches_ms_party and matches_gp and matches_transfer and matches_date:
                filtered_docs.append(doc)
        
        # Populate table with filtered documents
        try:
            self.table.setRowCount(len(filtered_docs))
            for row, doc in enumerate(filtered_docs):
                self.table.setItem(row, 0, QTableWidgetItem(doc.get('transfer_number', '')))
                self.table.setItem(row, 1, QTableWidgetItem(doc.get('gp_number', '')))
                self.table.setItem(row, 2, QTableWidgetItem(doc.get('sr_number', '')))
                self.table.setItem(row, 3, QTableWidgetItem(doc.get('ms_party_name', '')))
                self.table.setItem(row, 4, QTableWidgetItem(doc.get('from_party', '')))
                self.table.setItem(row, 5, QTableWidgetItem(doc.get('transfer_to', '')))
                self.table.setItem(row, 6, QTableWidgetItem(doc.get('vehicle_number', '')))
                self.table.setItem(row, 7, QTableWidgetItem(doc.get('driver_name', '')))
                self.table.setItem(row, 8, QTableWidgetItem(str(doc.get('total_quantity', 0))))
                date_str = doc.get('document_date', '')
                if date_str:
                    date_str = date_str[:10]
                self.table.setItem(row, 9, QTableWidgetItem(date_str))
                self.table.item(row, 0).setData(Qt.UserRole, doc.get('id'))
        except RuntimeError:
            # Widget was deleted during operation
            pass
    
    def clear_search(self):
        """Clear all search filters"""
        self.ms_party_filter.clear()
        self.gp_filter.clear()
        self.transfer_filter.clear()
        self.from_date_input.setDate(QDate(2000, 1, 1))
        self.to_date_input.setDate(QDate(2099, 12, 31))
        self.filter_table()
    
    def on_load_error(self, error):
        QMessageBox.warning(self, "Error", f"Failed to load documents: {error}")
        self.server_available = False
    
    def add_transfer(self):
        if not self.server_available:
            QMessageBox.warning(self, "Server Offline", "Server is not available.")
            return
        
        # Simple Transfer window: always create standard transfers here.
        transfer_type = 'simple'

        # Show party search dialog
        party_dialog = PartySearchDialog(self)
        if party_dialog.exec_() == QDialog.Accepted and party_dialog.selected_party:
            # Open transfer dialog with pre-selected party and transfer type
            dialog = TransferDialog(self, user_data=self.user_data, preselected_party=party_dialog.selected_party, transfer_type=transfer_type)
            if dialog.exec_() == QDialog.Accepted:
                saved = getattr(dialog, "saved_document", None)
                if isinstance(saved, dict) and saved.get("id"):
                    self._upsert_document(saved, prefer_top=True)
                else:
                    self.load_documents_async()
    
    def edit_selected_transfer(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        doc_id = self.table.item(row, 0).data(Qt.UserRole)
        
        try:
            response = self.api_client._try_request("GET", f"/api/transfer/{doc_id}")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    document = data.get("document")
                    dialog = TransferDialog(self, document=document, user_data=self.user_data)
                    if dialog.exec_() == QDialog.Accepted:
                        saved = getattr(dialog, "saved_document", None)
                        if isinstance(saved, dict) and saved.get("id"):
                            self._upsert_document(saved, prefer_top=False)
                        else:
                            self.load_documents_async()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load document: {str(e)}")
    
    def delete_selected_transfer(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        doc_id = self.table.item(row, 0).data(Qt.UserRole)
        doc_number = self.table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {doc_number}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                response = self.api_client._try_request_with_retry("DELETE", f"/api/transfer/{doc_id}")
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        QMessageBox.information(self, "Success", "Document deleted successfully")
                        self._remove_document_by_id(doc_id)
                    else:
                        QMessageBox.warning(self, "Error", data.get("message", "Failed to delete"))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")
    
    def print_transfers(self):
        """Show print dialog and print selected transfers"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one transfer document to print")
            return
        
        # Filter documents based on transfer type
        if hasattr(self, 'transfer_type_filter'):
            if self.transfer_type_filter == 'by_name':
                filtered_documents = [
                    doc for doc in self.all_documents
                    if doc.get('transfer_type', 'simple') == 'by_name'
                ]
            else:
                filtered_documents = [
                    doc for doc in self.all_documents
                    if doc.get('transfer_type', 'simple') != 'by_name'
                ]
        else:
            filtered_documents = self.all_documents
        dialog = PrintTransferDialog(self, selected_rows, filtered_documents)
        if dialog.exec_() == QDialog.Accepted:
            selected_ids = dialog.get_selected_ids()
            if selected_ids:
                self.generate_and_print_html(selected_ids)
    
    def find_logo_file(self):
        """Find logo file in common locations"""
        logo_names = ['logo.png', 'logo.jpg', 'logo.jpeg', 'logo.svg', 'company_logo.png', 'company_logo.jpg']
        search_paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'assets'),
            os.path.join(os.path.dirname(__file__), '..', 'assets'),
            os.path.join(os.getcwd(), 'assets'),
            os.path.join(os.getcwd(), 'images'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets'),
        ]
        
        for search_path in search_paths:
            if os.path.exists(search_path):
                for logo_name in logo_names:
                    logo_path = os.path.join(search_path, logo_name)
                    if os.path.exists(logo_path):
                        return os.path.abspath(logo_path)
        return None
    
    def generate_and_print_html(self, transfer_ids):
        """Generate HTML for printing and open in Chrome"""
        try:
            transfers = []
            for transfer_id in transfer_ids:
                response = self.api_client._try_request("GET", f"/api/transfer/{transfer_id}")
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        transfers.append(data.get("document"))
            
            if not transfers:
                QMessageBox.warning(self, "Error", "No transfer documents found to print")
                return
            
            html_content = self.generate_print_html(transfers)
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME', ''))
            ]
            
            chrome_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
            
            if chrome_path:
                import subprocess
                # Open in new tab instead of new window
                subprocess.Popen([chrome_path, '--new-tab', 'file://' + temp_file.name.replace('\\', '/')])
            else:
                webbrowser.open('file://' + temp_file.name)
                QMessageBox.information(
                    self, "Print", 
                    "Print dialog opened. Please use Ctrl+P or File > Print to print the document."
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate print document: {str(e)}")
    
    def generate_print_html(self, transfers):
        """Generate print-ready HTML for transfer documents"""
        html = self._get_base_html_styles()
        
        pages = []
        for i in range(0, len(transfers), 2):
            page_transfers = transfers[i:i+2]
            pages.append(page_transfers)
        
        for page_idx, page_transfers in enumerate(pages):
            html += '<div class="page">\n'
            
            for form_idx, transfer in enumerate(page_transfers):
                html += self.generate_transfer_form_html(transfer)
                
                if form_idx < len(page_transfers) - 1:
                    html += '<div class="cut-line"></div>\n'
            
            html += '</div>\n'
        
        html += """
    <script>
        window.onload = function() {
            window.print();
        };
    </script>
</body>
</html>
"""
        return html
    
    def _get_base_html_styles(self):
        """Get base HTML styles (shared between Transfer and Outward)"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Print Documents</title>
    <style>
        @page {
            size: A4 portrait;
            margin: 0;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: Arial, sans-serif;
            font-size: 12px;
            background: white;
            padding: 10mm;
            color: #1a1a1a;
        }
        
        .page {
            width: 210mm;
            min-height: 297mm;
            page-break-after: always;
            position: relative;
        }
        
        .page:last-child {
            page-break-after: auto;
        }
        
        .form {
            width: 100%;
            border: 1px solid #000;
            padding: 8mm;
            margin-bottom: 5mm;
        }
        
        .form:last-child {
            margin-bottom: 0;
        }
        
        .cut-line {
            border-top: 2px dashed #666;
            margin: 5mm 0;
            width: 100%;
        }
        
        .header {
            text-align: center;
            margin-bottom: 8mm;
            position: relative;
        }
        
        .company-name {
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 3mm;
            color: #0066cc;
        }
        
        .logo {
            position: absolute;
            right: 0;
            top: 0;
            width: 45mm;
            height: 45mm;
            background: transparent;
        }
        
        .logo img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            background: transparent;
            mix-blend-mode: multiply;
        }
        
        .owner-info {
            text-align: center;
            font-size: 11px;
            margin-bottom: 2mm;
            color: #333333;
        }
        
        .subtitle {
            text-align: center;
            font-size: 16px;
            font-weight: bold;
            margin: 5mm 0;
            text-decoration: underline;
            color: #cc0000;
        }
        
        .meta-info {
            margin-bottom: 5mm;
        }
        
        .meta-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 2mm;
            font-size: 11px;
            color: #1a1a1a;
        }
        
        .meta-item {
            flex: 1;
            margin-right: 5mm;
        }
        
        .meta-item:last-child {
            margin-right: 0;
        }
        
        .meta-label {
            font-weight: bold;
            display: inline-block;
            min-width: 60px;
            color: #0066cc;
        }
        
        .meta-value {
            border-bottom: 1px solid #333;
            display: inline-block;
            min-width: 100px;
            padding: 0 2mm;
            color: #cc0000;
            font-weight: 500;
        }
        
        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 5mm;
        }
        
        .items-table th,
        .items-table td {
            border: 1px solid #333;
            padding: 2mm;
            text-align: left;
        }
        
        .items-table th {
            background-color: #e6f2ff;
            font-weight: bold;
            text-align: center;
            color: #0066cc;
        }
        
        .items-table td {
            text-align: center;
            color: #1a1a1a;
        }
        
        .items-table tbody tr:nth-child(even) td {
            background-color: #f9f9f9;
        }
        
        .footer {
            margin-top: 5mm;
            font-size: 10px;
        }
        
        .footer-row {
            margin-bottom: 1mm;
        }
        
        .footer-label {
            font-weight: bold;
            display: inline-block;
            min-width: 80px;
            color: #0066cc;
        }
        
        .footer-value {
            border-bottom: 1px solid #333;
            display: inline-block;
            min-width: 150px;
            padding: 0 2mm;
            color: #cc0000;
            font-weight: 500;
        }
        
        .site-info {
            text-align: center;
            margin-top: 3mm;
            font-size: 10px;
            color: #006600;
            font-weight: 500;
        }
        
        .contacts {
            text-align: center;
            margin-top: 1mm;
            font-size: 10px;
            color: #cc6600;
            font-weight: 500;
        }
        
        @media print {
            body {
                padding: 0;
            }
            
            .page {
                margin: 0;
                padding: 10mm;
            }
            
            .cut-line {
                page-break-inside: avoid;
            }
            
            .form {
                page-break-inside: avoid;
            }
        }
    </style>
</head>
<body>
"""
    
    def generate_transfer_form_html(self, transfer):
        """Generate HTML for a single transfer form"""
        items = transfer.get('items', [])
        
        doc_date = transfer.get('document_date', '')
        if doc_date:
            try:
                date_obj = datetime.strptime(doc_date[:10], '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d-%m-%Y')
            except:
                formatted_date = doc_date[:10]
        else:
            formatted_date = ''
        
        logo_path = self.find_logo_file()
        logo_html = ''
        if logo_path:
            try:
                with open(logo_path, 'rb') as logo_file:
                    logo_data = logo_file.read()
                    logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                    logo_ext = os.path.splitext(logo_path)[1].lower()
                    mime_type = 'image/png' if logo_ext == '.png' else 'image/jpeg' if logo_ext in ['.jpg', '.jpeg'] else 'image/svg+xml' if logo_ext == '.svg' else 'image/png'
                    logo_html = f'<img src="data:{mime_type};base64,{logo_base64}" alt="Logo" style="background: transparent; width: 100%; height: 100%; object-fit: contain;" />'
            except:
                logo_html = f'<img src="{logo_path}" alt="Logo" style="background: transparent; width: 100%; height: 100%; object-fit: contain;" />'
        else:
            logo_html = '<div style="width: 100%; height: 100%; background: transparent; border: 1px dashed #ccc; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #999;">LOGO</div>'
        
        html = f"""
    <div class="form">
        <div class="header">
            <div class="logo">{logo_html}</div>
            <div class="company-name">MOMINA LACE DYEING</div>
            <div class="owner-info">
                Owner : GHULAM MUSTAFA<br>
                GM    : Shahid, Naveed
            </div>
        </div>
        
        <div class="subtitle">GOODS TRANSFER</div>
        
        <div class="meta-info">
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">SR# :</span>
                    <span class="meta-value">{transfer.get('sr_number', '')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">DATE :</span>
                    <span class="meta-value">{formatted_date}</span>
                </div>
            </div>
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">MS PARTY :</span>
                    <span class="meta-value">{transfer.get('ms_party_name', '')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">FROM :</span>
                    <span class="meta-value">{transfer.get('from_party', '')}</span>
                </div>
            </div>
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">TRANSFER TO :</span>
                    <span class="meta-value">{transfer.get('transfer_to', '')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">VEHICLE NO :</span>
                    <span class="meta-value">{transfer.get('vehicle_number', '')}</span>
                </div>
            </div>
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">DRIVER :</span>
                    <span class="meta-value">{transfer.get('driver_name', '')}</span>
                </div>
                <div class="meta-item">
                </div>
            </div>
        </div>
        
        <table class="items-table">
            <thead>
                <tr>
                    <th style="width: 20%;">QTY (Than)</th>
                    <th style="width: 50%;">DETAILS (Item Name)</th>
                    <th style="width: 30%;">YARDS</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for item in items:
            qty = item.get('quantity', 0)
            item_name = item.get('item_name', '')
            measurement = item.get('measurement', '')
            html += f"""
                <tr>
                    <td>{qty}</td>
                    <td>{item_name}</td>
                    <td>{measurement}</td>
                </tr>
"""
        
        empty_rows = max(0, 3 - len(items))
        for _ in range(empty_rows):
            html += """
                <tr>
                    <td></td>
                    <td></td>
                    <td></td>
                </tr>
"""
        
        html += f"""
            </tbody>
        </table>
        
        <div class="footer">
            <div class="footer-row">
                <span class="footer-label">CREATED BY :</span>
                <span class="footer-value">{transfer.get('created_by', '')}</span>
            </div>
            <div class="footer-row">
                <span class="footer-label">EDITED BY :</span>
                <span class="footer-value">{transfer.get('edited_by', 'None') if transfer.get('edited_by') else 'None'}</span>
            </div>
            {('' if not transfer.get('edit_log_history') else f'<div class="footer-row"><span class="footer-label">EDIT LOG HISTORY :</span><span class="footer-value" style="font-size: 10px;">{transfer.get("edit_log_history", "None")}</span></div>')}
            <div class="site-info">
                SITE:<br>
                Small Industrial State, Sargodha Road, Faisalabad
            </div>
            <div class="contacts">
                CONTACTS:<br>
                0321-7651815, 0300-8651815<br>
                0304-6166663, 0300-8636129
            </div>
        </div>
    </div>
"""
        return html


class PrintTransferDialog(QDialog):
    """Dialog for selecting transfers to print"""
    
    def __init__(self, parent=None, selected_rows=None, all_documents=None):
        super().__init__(parent)
        self.selected_ids = []
        self.all_documents = all_documents or []
        self.selected_rows = selected_rows or set()
        self.setWindowTitle("Print Transfer Documents")
        self.setMinimumSize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        instructions = QLabel("Select transfer documents to print:")
        instructions.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        layout.addWidget(instructions)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        
        for idx, doc in enumerate(self.all_documents):
            item_text = f"{doc.get('transfer_number', '')} - {doc.get('ms_party_name', '')} - {doc.get('document_date', '')[:10]}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, doc.get('id'))
            
            if idx in self.selected_rows:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            self.list_widget.addItem(item)
        
        layout.addWidget(self.list_widget)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        deselect_all_btn.clicked.connect(self.deselect_all)
        button_layout.addWidget(deselect_all_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
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
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        print_btn = QPushButton("Print")
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #107c10;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0d5f0d;
            }
        """)
        print_btn.clicked.connect(self.accept)
        button_layout.addWidget(print_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def select_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Checked)
    
    def deselect_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Unchecked)
    
    def get_selected_ids(self):
        selected_ids = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                transfer_id = item.data(Qt.UserRole)
                if transfer_id:
                    selected_ids.append(transfer_id)
        return selected_ids


class TransferBNModule(QWidget):
    """Separate module for managing Transfer By Name (BN) documents only."""
    
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data
        self.server_available = True
        self.ws_bus = (user_data or {}).get("ws_bus")
        self.api_client = APIClient()
        # Set username on API client for edited_by tracking
        if user_data and user_data.get('username'):
            self.api_client.set_username(user_data.get('username'))
        self._data_loaded = False  # Track if data has been loaded
        self._setup_realtime("transfer")
        self.init_ui()
        # Don't load data immediately - wait until module is shown
        self.transfer_type_filter = 'by_name'  # Filter for print dialog
    
    def load_data_if_needed(self):
        """Load data if not already loaded (called explicitly when module is shown)"""
        if not self._data_loaded:
            self._data_loaded = True
            self.load_documents_async()
    
    def showEvent(self, event):
        """Handle show event (but don't load here - use load_data_if_needed instead)"""
        super().showEvent(event)

    def _setup_realtime(self, entity: str):
        """Wire up WebSocket → Qt bus for real-time UI patching."""
        self.realtime_entity = entity
        if self.ws_bus:
            try:
                self.ws_bus.message.connect(self.on_realtime_message)
            except Exception:
                pass

    def on_realtime_message(self, message: dict):
        """Apply server-pushed CRUD updates (so client UIs update instantly)."""
        if not isinstance(message, dict):
            return
        if message.get("type") != "entity_change":
            return
        if message.get("entity") != getattr(self, "realtime_entity", None):
            return

        action = message.get("action")
        data = message.get("data") or {}
        
        # For delete actions, check if document exists in our list (to verify it's a by_name transfer)
        if action == "deleted":
            doc_id = data.get("id") if isinstance(data, dict) else None
            if doc_id:
                # Check if this document exists in our all_documents (meaning it's a by_name transfer)
                if hasattr(self, "all_documents") and self.all_documents:
                    doc_exists = any(d.get("id") == doc_id for d in self.all_documents)
                    if doc_exists:
                        self._remove_document_by_id(doc_id)
            return
        
        # For create/update, only process by_name transfers
        if isinstance(data, dict) and data.get("transfer_type") != "by_name":
            return
        
        if action in ("created", "updated"):
            if isinstance(data, dict) and data.get("id"):
                self._upsert_document(data, prefer_top=(action == "created"))

    def _upsert_document(self, doc: dict, prefer_top: bool = False):
        """Insert or update a document in-memory and refresh table view."""
        # Safety check: ensure widget still exists
        if not hasattr(self, 'table') or self.table is None:
            return
        try:
            _ = self.table.objectName()
        except RuntimeError:
            # Widget was deleted, ignore update
            return
        
        if not hasattr(self, "all_documents") or self.all_documents is None:
            self.all_documents = []

        doc_id = doc.get("id")
        if not doc_id:
            return

        existing_idx = next((i for i, d in enumerate(self.all_documents) if d.get("id") == doc_id), None)
        if existing_idx is None:
            if prefer_top:
                self.all_documents.insert(0, doc)
            else:
                self.all_documents.append(doc)
        else:
            self.all_documents[existing_idx] = doc

        self.filter_table()

    def _remove_document_by_id(self, doc_id: int):
        """Remove a document from in-memory list and refresh table view."""
        # Safety check: ensure widget still exists
        if not hasattr(self, 'table') or self.table is None:
            return
        try:
            _ = self.table.objectName()
        except RuntimeError:
            # Widget was deleted, ignore update
            return
        
        if not hasattr(self, "all_documents"):
            self.all_documents = []
        
        # Remove the document from the list
        self.all_documents = [d for d in self.all_documents if d.get("id") != doc_id]
        
        # Always refresh the table, even if all_documents is now empty
        self.filter_table()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("🔤 Transfers BN")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)
        header.addStretch()
        
        self.add_btn = QPushButton("➕ Add Transfer BN")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.add_btn.clicked.connect(self.add_transfer)
        header.addWidget(self.add_btn)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        self.refresh_btn.clicked.connect(self.load_documents_async)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # Filter bar (MS Party, Transfer BN #, date range)
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        ms_party_label = QLabel("MS Party:")
        ms_party_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        filter_layout.addWidget(ms_party_label)
        
        self.ms_party_filter = QLineEdit()
        self.ms_party_filter.setPlaceholderText("Filter by MS Party...")
        self.ms_party_filter.setStyleSheet("""
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
        self.ms_party_filter.textChanged.connect(self.filter_table)
        filter_layout.addWidget(self.ms_party_filter)
        
        transfer_bn_label = QLabel("Transfer BN #:")
        transfer_bn_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        filter_layout.addWidget(transfer_bn_label)
        
        self.transfer_bn_filter = QLineEdit()
        self.transfer_bn_filter.setPlaceholderText("Filter by Transfer BN #...")
        self.transfer_bn_filter.setStyleSheet("""
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
        self.transfer_bn_filter.textChanged.connect(self.filter_table)
        self.transfer_bn_filter.textChanged.connect(self.auto_uppercase_text)
        filter_layout.addWidget(self.transfer_bn_filter)
        
        date_label = QLabel("From:")
        date_label.setStyleSheet("color: #ffffff;")
        filter_layout.addWidget(date_label)
        
        self.from_date_input = QDateEdit()
        self.from_date_input.setDate(QDate(2000, 1, 1))
        self.from_date_input.setCalendarPopup(True)
        self.from_date_input.setStyleSheet("""
            QDateEdit {
                background-color: #2a2a2a;
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
            }
            QDateEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        self.from_date_input.dateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.from_date_input)
        
        to_label = QLabel("To:")
        to_label.setStyleSheet("color: #ffffff;")
        filter_layout.addWidget(to_label)
        
        self.to_date_input = QDateEdit()
        self.to_date_input.setDate(QDate(2099, 12, 31))
        self.to_date_input.setCalendarPopup(True)
        self.to_date_input.setStyleSheet("""
            QDateEdit {
                background-color: #2a2a2a;
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
            }
            QDateEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        self.to_date_input.dateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.to_date_input)
        
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
        filter_layout.addWidget(clear_btn)
        
        layout.addLayout(filter_layout)
        
        # Setup autocomplete for MS Party filter
        self.setup_ms_party_autocomplete()
        
        # Store original documents for filtering
        self.all_documents = []
        
        # Table for By Name Transfers
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Transfer BN #", "SR #", "MS Party", "From Party",
            "Transfer To Party", "Total Qty", "Date"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #252525;
                border: 1px solid #3d3d3d;
                gridline-color: #3d3d3d;
                color: #ffffff;
            }
            QTableWidget::item {
                padding: 5px;
                background-color: #1e1e1e;
            }
            QTableWidget::item:alternate {
                background-color: #252525;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                padding: 8px;
                border: none;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.edit_selected_transfer)
        # Set column widths to ensure headers display properly
        self.table.setColumnWidth(0, 140)  # Transfer BN #
        self.table.setColumnWidth(1, 80)   # SR #
        self.table.setColumnWidth(2, 140)  # MS Party
        self.table.setColumnWidth(3, 140)  # From Party
        self.table.setColumnWidth(4, 180)  # Transfer To Party (longest header)
        self.table.setColumnWidth(5, 100)  # Total Qty
        # Date column (index 6) will stretch due to setStretchLastSection(True)
        layout.addWidget(self.table)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.clicked.connect(self.edit_selected_transfer)
        self.edit_btn.setEnabled(False)
        action_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self.delete_selected_transfer)
        self.delete_btn.setEnabled(False)
        action_layout.addWidget(self.delete_btn)
        
        self.print_btn = QPushButton("🖨️ Print")
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #107c10;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0d5f0d;
            }
        """)
        self.print_btn.clicked.connect(self.print_transfers)
        action_layout.addWidget(self.print_btn)
        
        layout.addLayout(action_layout)
        
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        self.setLayout(layout)
    
    def on_selection_changed(self):
        has_selection = len(self.table.selectedItems()) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def load_documents_async(self):
        """Load all transfer documents (will filter to by_name only in filter_table)."""
        self.loader = DocumentLoader("transfer")
        self.loader.finished.connect(self.populate_table)
        self.loader.error.connect(self.on_load_error)
        self.loader.start()
    
    def populate_table(self, documents):
        """Populate table with By Name transfers only."""
        # Store all documents for filtering
        self.all_documents = documents
        self.filter_table()
    
    def filter_table(self):
        """Filter table based on search criteria - only show by_name transfers."""
        # Safety check: ensure widget still exists
        if not hasattr(self, 'table') or self.table is None:
            return
        try:
            _ = self.table.objectName()
        except RuntimeError:
            # Widget was deleted
            return
        
        if not hasattr(self, 'all_documents'):
            self.all_documents = []
        
        # If all_documents is empty, clear the table
        if not self.all_documents:
            try:
                self.table.setRowCount(0)
            except RuntimeError:
                pass
            return
        
        # Get filter values
        ms_party_filter = ""
        transfer_bn_filter = ""
        from_date = QDate(2000, 1, 1)
        to_date = QDate(2099, 12, 31)
        
        try:
            if hasattr(self, 'ms_party_filter') and self.ms_party_filter is not None:
                ms_party_filter = self.ms_party_filter.text().upper()
            if hasattr(self, 'transfer_bn_filter') and self.transfer_bn_filter is not None:
                transfer_bn_filter = self.transfer_bn_filter.text().upper()
            if hasattr(self, 'from_date_input') and self.from_date_input is not None:
                from_date = self.from_date_input.date()
            if hasattr(self, 'to_date_input') and self.to_date_input is not None:
                to_date = self.to_date_input.date()
        except RuntimeError:
            # Widgets were deleted
            pass
        
        filtered_docs = []
        for doc in self.all_documents:
            # Only show by_name transfers
            doc_transfer_type = doc.get('transfer_type', 'simple')
            if doc_transfer_type != 'by_name':
                continue
            
            # Check MS Party filter
            matches_ms_party = True
            if ms_party_filter:
                ms_party = doc.get('ms_party_name', '').upper()
                matches_ms_party = ms_party_filter in ms_party
            
            # Check Transfer BN # filter
            matches_transfer_bn = True
            if transfer_bn_filter:
                transfer_bn = doc.get('transfer_number', '').upper()
                matches_transfer_bn = transfer_bn_filter in transfer_bn
            
            # Check date range
            matches_date = True
            doc_date_str = doc.get('document_date', '')
            if doc_date_str:
                try:
                    doc_date = QDate.fromString(doc_date_str[:10], "yyyy-MM-dd")
                    matches_date = from_date <= doc_date <= to_date
                except:
                    matches_date = True
            
            # All filters must match (AND logic)
            if matches_ms_party and matches_transfer_bn and matches_date:
                filtered_docs.append(doc)
        
        # Populate table with filtered documents
        try:
            self.table.setRowCount(len(filtered_docs))
            for row, doc in enumerate(filtered_docs):
                self.table.setItem(row, 0, QTableWidgetItem(doc.get('transfer_number', '')))
                self.table.setItem(row, 1, QTableWidgetItem(doc.get('sr_number', '')))
                self.table.setItem(row, 2, QTableWidgetItem(doc.get('ms_party_name', '')))
                self.table.setItem(row, 3, QTableWidgetItem(doc.get('from_party', '')))
                self.table.setItem(row, 4, QTableWidgetItem(doc.get('transfer_to', '')))
                self.table.setItem(row, 5, QTableWidgetItem(str(doc.get('total_quantity', 0))))
                date_str = doc.get('document_date', '')
                if date_str:
                    date_str = date_str[:10]
                self.table.setItem(row, 6, QTableWidgetItem(date_str))
                self.table.item(row, 0).setData(Qt.UserRole, doc.get('id'))
        except RuntimeError:
            # Widget was deleted during operation
            pass
    
    def clear_search(self):
        self.ms_party_filter.clear()
        self.transfer_bn_filter.clear()
        self.from_date_input.setDate(QDate(2000, 1, 1))
        self.to_date_input.setDate(QDate(2099, 12, 31))
        self.filter_table()
    
    def on_load_error(self, error):
        QMessageBox.warning(self, "Error", f"Failed to load documents: {error}")
        self.server_available = False
    
    def setup_ms_party_autocomplete(self):
        """Set up autocomplete for MS Party filter"""
        try:
            # Get MS parties only (from party management module)
            response = self.api_client._try_request("GET", "/api/parties")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    parties = data.get("parties", [])
                    active_parties = [p for p in parties if p.get('is_active', True)]
                    party_names = [party['name'] for party in active_parties]
                    
                    from PyQt5.QtWidgets import QCompleter
                    from PyQt5.QtCore import Qt
                    completer = QCompleter(party_names, self.ms_party_filter)
                    completer.setCaseSensitivity(Qt.CaseInsensitive)
                    completer.setCompletionMode(QCompleter.PopupCompletion)
                    completer.setFilterMode(Qt.MatchContains)
                    completer.setMaxVisibleItems(10)
                    self.ms_party_filter.setCompleter(completer)
                    
                    # Style the completer popup
                    completer.popup().setStyleSheet("""
                        QListView {
                            background-color: #1e1e1e;
                            border: 1px solid #3d3d3d;
                            color: #ffffff;
                            selection-background-color: #0078d4;
                            selection-color: #ffffff;
                            padding: 2px;
                        }
                    """)
        except:
            pass
    
    def auto_uppercase_text(self, text):
        """Automatically convert text to uppercase as user types (except MS Party filter)"""
        sender = self.sender()
        if sender and sender != self.ms_party_filter:  # Don't uppercase MS Party filter (for autocomplete)
            cursor_pos = sender.cursorPosition()
            uppercase_text = text.upper()
            if text != uppercase_text:
                sender.blockSignals(True)
                sender.setText(uppercase_text)
                sender.setCursorPosition(min(cursor_pos, len(uppercase_text)))
                sender.blockSignals(False)
    
    def clear_search(self):
        """Clear all search filters"""
        self.ms_party_filter.clear()
        self.transfer_bn_filter.clear()
        self.from_date_input.setDate(QDate(2000, 1, 1))
        self.to_date_input.setDate(QDate(2099, 12, 31))
        self.filter_table()
    
    def add_transfer(self):
        if not self.server_available:
            QMessageBox.warning(self, "Server Offline", "Server is not available.")
            return
        
        # Show party search dialog
        party_dialog = PartySearchDialog(self)
        if party_dialog.exec_() == QDialog.Accepted and party_dialog.selected_party:
            # Open transfer dialog with pre-selected party and transfer type
            dialog = TransferDialog(self, user_data=self.user_data, preselected_party=party_dialog.selected_party, transfer_type='by_name')
            if dialog.exec_() == QDialog.Accepted:
                saved = getattr(dialog, "saved_document", None)
                if isinstance(saved, dict) and saved.get("id"):
                    self._upsert_document(saved, prefer_top=True)
                else:
                    self.load_documents_async()
    
    def edit_selected_transfer(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        doc_id = self.table.item(row, 0).data(Qt.UserRole)
        
        try:
            response = self.api_client._try_request("GET", f"/api/transfer/{doc_id}")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    document = data.get("document")
                    dialog = TransferDialog(self, document=document, user_data=self.user_data, transfer_type='by_name')
                    if dialog.exec_() == QDialog.Accepted:
                        saved = getattr(dialog, "saved_document", None)
                        if isinstance(saved, dict) and saved.get("id"):
                            self._upsert_document(saved, prefer_top=False)
                        else:
                            self.load_documents_async()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load document: {str(e)}")
    
    def delete_selected_transfer(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        doc_id = self.table.item(row, 0).data(Qt.UserRole)
        doc_number = self.table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {doc_number}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                response = self.api_client._try_request_with_retry("DELETE", f"/api/transfer/{doc_id}")
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        QMessageBox.information(self, "Success", "Document deleted successfully")
                        self._remove_document_by_id(doc_id)
                    else:
                        QMessageBox.warning(self, "Error", data.get("message", "Failed to delete"))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")
    
    def print_transfers(self):
        """Show print dialog and print selected transfers"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one transfer document to print")
            return
        
        # Filter documents based on transfer type
        if hasattr(self, 'transfer_type_filter'):
            if self.transfer_type_filter == 'by_name':
                filtered_documents = [
                    doc for doc in self.all_documents
                    if doc.get('transfer_type', 'simple') == 'by_name'
                ]
            else:
                filtered_documents = [
                    doc for doc in self.all_documents
                    if doc.get('transfer_type', 'simple') != 'by_name'
                ]
        else:
            filtered_documents = self.all_documents
        dialog = PrintTransferDialog(self, selected_rows, filtered_documents)
        if dialog.exec_() == QDialog.Accepted:
            selected_ids = dialog.get_selected_ids()
            if selected_ids:
                self.generate_and_print_html(selected_ids)
    
    def find_logo_file(self):
        """Find logo file in common locations"""
        logo_names = ['logo.png', 'logo.jpg', 'logo.jpeg', 'logo.svg', 'company_logo.png', 'company_logo.jpg']
        search_paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'assets'),
            os.path.join(os.path.dirname(__file__), '..', 'assets'),
            os.path.join(os.getcwd(), 'assets'),
            os.path.join(os.getcwd(), 'images'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets'),
        ]
        
        for search_path in search_paths:
            if os.path.exists(search_path):
                for logo_name in logo_names:
                    logo_path = os.path.join(search_path, logo_name)
                    if os.path.exists(logo_path):
                        return os.path.abspath(logo_path)
        return None
    
    def generate_and_print_html(self, transfer_ids):
        """Generate HTML for printing and open in Chrome"""
        try:
            transfers = []
            for transfer_id in transfer_ids:
                response = self.api_client._try_request("GET", f"/api/transfer/{transfer_id}")
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        transfers.append(data.get("document"))
            
            if not transfers:
                QMessageBox.warning(self, "Error", "No transfer documents found to print")
                return
            
            html_content = self.generate_print_html(transfers)
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME', ''))
            ]
            
            chrome_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
            
            if chrome_path:
                import subprocess
                # Open in new tab instead of new window
                subprocess.Popen([chrome_path, '--new-tab', 'file://' + temp_file.name.replace('\\', '/')])
            else:
                webbrowser.open('file://' + temp_file.name)
                QMessageBox.information(
                    self, "Print", 
                    "Print dialog opened. Please use Ctrl+P or File > Print to print the document."
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate print document: {str(e)}")
    
    def generate_print_html(self, transfers):
        """Generate print-ready HTML for transfer documents (reuse from TransferModule)"""
        # Reuse the same print HTML generation logic as TransferModule
        # This method can be shared or we can import it
        html = self._get_base_html_styles()
        
        pages = []
        for i in range(0, len(transfers), 2):
            page_transfers = transfers[i:i+2]
            pages.append(page_transfers)
        
        for page_idx, page_transfers in enumerate(pages):
            html += '<div class="page">\n'
            
            for form_idx, transfer in enumerate(page_transfers):
                html += self.generate_transfer_form_html(transfer)
                
                if form_idx < len(page_transfers) - 1:
                    html += '<div class="cut-line"></div>\n'
            
            html += '</div>\n'
        
        html += """
    <script>
        window.onload = function() {
            window.print();
        };
    </script>
</body>
</html>
"""
        return html
    
    def _get_base_html_styles(self):
        """Get base HTML styles (shared between Transfer and Outward)"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Print Documents</title>
    <style>
        @page {
            size: A4 portrait;
            margin: 0;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: Arial, sans-serif;
            font-size: 12px;
            background: white;
            padding: 10mm;
            color: #1a1a1a;
        }
        
        .page {
            width: 210mm;
            min-height: 297mm;
            page-break-after: always;
            position: relative;
        }
        
        .page:last-child {
            page-break-after: auto;
        }
        
        .form {
            width: 100%;
            border: 1px solid #000;
            padding: 8mm;
            margin-bottom: 5mm;
        }
        
        .form:last-child {
            margin-bottom: 0;
        }
        
        .cut-line {
            border-top: 2px dashed #666;
            margin: 5mm 0;
            width: 100%;
        }
        
        .header {
            text-align: center;
            margin-bottom: 8mm;
            position: relative;
        }
        
        .company-name {
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 3mm;
            color: #0066cc;
        }
        
        .logo {
            position: absolute;
            right: 0;
            top: 0;
            width: 45mm;
            height: 45mm;
            background: transparent;
        }
        
        .logo img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            background: transparent;
            mix-blend-mode: multiply;
        }
        
        .owner-info {
            text-align: center;
            font-size: 11px;
            margin-bottom: 2mm;
            color: #333333;
        }
        
        .subtitle {
            text-align: center;
            font-size: 16px;
            font-weight: bold;
            margin: 5mm 0;
            text-decoration: underline;
            color: #cc0000;
        }
        
        .meta-info {
            margin-bottom: 5mm;
        }
        
        .meta-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 2mm;
            font-size: 11px;
            color: #1a1a1a;
        }
        
        .meta-item {
            flex: 1;
            margin-right: 5mm;
        }
        
        .meta-item:last-child {
            margin-right: 0;
        }
        
        .meta-label {
            font-weight: bold;
            display: inline-block;
            min-width: 60px;
            color: #0066cc;
        }
        
        .meta-value {
            border-bottom: 1px solid #333;
            display: inline-block;
            min-width: 100px;
            padding: 0 2mm;
            color: #cc0000;
            font-weight: 500;
        }
        
        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 5mm;
        }
        
        .items-table th,
        .items-table td {
            border: 1px solid #333;
            padding: 2mm;
            text-align: left;
        }
        
        .items-table th {
            background-color: #e6f2ff;
            font-weight: bold;
            text-align: center;
            color: #0066cc;
        }
        
        .items-table td {
            text-align: center;
            color: #1a1a1a;
        }
        
        .items-table tbody tr:nth-child(even) td {
            background-color: #f9f9f9;
        }
        
        .footer {
            margin-top: 5mm;
            font-size: 10px;
        }
        
        .footer-row {
            margin-bottom: 1mm;
        }
        
        .footer-label {
            font-weight: bold;
            display: inline-block;
            min-width: 80px;
            color: #0066cc;
        }
        
        .footer-value {
            border-bottom: 1px solid #333;
            display: inline-block;
            min-width: 150px;
            padding: 0 2mm;
            color: #cc0000;
            font-weight: 500;
        }
        
        .site-info {
            text-align: center;
            margin-top: 3mm;
            font-size: 10px;
            color: #006600;
            font-weight: 500;
        }
        
        .contacts {
            text-align: center;
            margin-top: 1mm;
            font-size: 10px;
            color: #cc6600;
            font-weight: 500;
        }
        
        @media print {
            body {
                padding: 0;
            }
            
            .page {
                margin: 0;
                padding: 10mm;
            }
            
            .cut-line {
                page-break-inside: avoid;
            }
            
            .form {
                page-break-inside: avoid;
            }
        }
    </style>
</head>
<body>
"""
    
    def generate_transfer_form_html(self, transfer):
        """Generate HTML for a single transfer form"""
        items = transfer.get('items', [])
        
        doc_date = transfer.get('document_date', '')
        if doc_date:
            try:
                date_obj = datetime.strptime(doc_date[:10], '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d-%m-%Y')
            except:
                formatted_date = doc_date[:10]
        else:
            formatted_date = ''
        
        logo_path = self.find_logo_file()
        logo_html = ''
        if logo_path:
            try:
                with open(logo_path, 'rb') as logo_file:
                    logo_data = logo_file.read()
                    logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                    logo_ext = os.path.splitext(logo_path)[1].lower()
                    mime_type = 'image/png' if logo_ext == '.png' else 'image/jpeg' if logo_ext in ['.jpg', '.jpeg'] else 'image/svg+xml' if logo_ext == '.svg' else 'image/png'
                    logo_html = f'<img src="data:{mime_type};base64,{logo_base64}" alt="Logo" style="background: transparent; width: 100%; height: 100%; object-fit: contain;" />'
            except:
                logo_html = f'<img src="{logo_path}" alt="Logo" style="background: transparent; width: 100%; height: 100%; object-fit: contain;" />'
        else:
            logo_html = '<div style="width: 100%; height: 100%; background: transparent; border: 1px dashed #ccc; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #999;">LOGO</div>'
        
        html = f"""
    <div class="form">
        <div class="header">
            <div class="logo">{logo_html}</div>
            <div class="company-name">MOMINA LACE DYEING</div>
            <div class="owner-info">
                Owner : GHULAM MUSTAFA<br>
                GM    : Shahid, Naveed
            </div>
        </div>
        
        <div class="subtitle">GOODS TRANSFER</div>
        
        <div class="meta-info">
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">SR# :</span>
                    <span class="meta-value">{transfer.get('sr_number', '')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">DATE :</span>
                    <span class="meta-value">{formatted_date}</span>
                </div>
            </div>
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">MS PARTY :</span>
                    <span class="meta-value">{transfer.get('ms_party_name', '')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">FROM :</span>
                    <span class="meta-value">{transfer.get('from_party', '')}</span>
                </div>
            </div>
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">TRANSFER TO :</span>
                    <span class="meta-value">{transfer.get('transfer_to', '')}</span>
                </div>
                <div class="meta-item">
                </div>
            </div>
        </div>
        
        <table class="items-table">
            <thead>
                <tr>
                    <th style="width: 20%;">QTY (Than)</th>
                    <th style="width: 50%;">DETAILS (Item Name)</th>
                    <th style="width: 30%;">YARDS</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for item in items:
            qty = item.get('quantity', 0)
            item_name = item.get('item_name', '')
            measurement = item.get('measurement', '')
            html += f"""
                <tr>
                    <td>{qty}</td>
                    <td>{item_name}</td>
                    <td>{measurement}</td>
                </tr>
"""
        
        empty_rows = max(0, 3 - len(items))
        for _ in range(empty_rows):
            html += """
                <tr>
                    <td></td>
                    <td></td>
                    <td></td>
                </tr>
"""
        
        html += f"""
            </tbody>
        </table>
        
        <div class="footer">
            <div class="footer-row">
                <span class="footer-label">CREATED BY :</span>
                <span class="footer-value">{transfer.get('created_by', '')}</span>
            </div>
            <div class="footer-row">
                <span class="footer-label">EDITED BY :</span>
                <span class="footer-value">{transfer.get('edited_by', 'None') if transfer.get('edited_by') else 'None'}</span>
            </div>
            {('' if not transfer.get('edit_log_history') else f'<div class="footer-row"><span class="footer-label">EDIT LOG HISTORY :</span><span class="footer-value" style="font-size: 10px;">{transfer.get("edit_log_history", "None")}</span></div>')}
            <div class="site-info">
                SITE:<br>
                Small Industrial State, Sargodha Road, Faisalabad
            </div>
            <div class="contacts">
                CONTACTS:<br>
                0321-7651815, 0300-8651815<br>
                0304-6166663, 0300-8636129
            </div>
        </div>
    </div>
"""
        return html


class TransferDialog(QDialog):
    """Dialog for adding/editing transfer document"""
    
    def __init__(self, parent=None, document=None, user_data=None, preselected_party=None, transfer_type='simple'):
        super().__init__(parent)
        self.document = document
        self.user_data = user_data
        self.saved_document = None  # returned by server for instant UI patching
        self.preselected_party = preselected_party
        self.transfer_type = transfer_type  # 'simple' or 'by_name'
        # If editing, get transfer_type from document
        if document and not transfer_type:
            self.transfer_type = document.get('transfer_type', 'simple')
        self.parties_with_stock = []
        self.available_stock = {}
        self.original_document_quantities = {}  # Store original quantities when editing
        self.ms_parties_list = []  # For By Name Transfer autocomplete
        self.api_client = APIClient()
        # Set username on API client for edited_by tracking
        if user_data and user_data.get('username'):
            self.api_client.set_username(user_data.get('username'))
        title = "Edit Transfer" if document else "Add Transfer"
        if self.transfer_type == 'by_name':
            title += " (By Name)"
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        self.init_ui()
        self.load_parties_with_stock()
        
        # Set up autocomplete after a short delay to ensure UI is fully initialized
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.setup_autocomplete)
        
        # If party was pre-selected, set it and load stock
        if self.preselected_party and not self.document:
            party_id = self.preselected_party.get('id')
            for i in range(self.ms_party_combo.count()):
                if self.ms_party_combo.itemData(i) == party_id:
                    self.ms_party_combo.setCurrentIndex(i)
                    break
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # MS Party (must select first)
        self.ms_party_combo = QComboBox()
        self.ms_party_combo.setEditable(False)  # Not editable, must select from dropdown
        self.ms_party_combo.setStyleSheet(self.get_combo_style())
        self.ms_party_combo.addItem("-- Select MS Party --", None)  # Default option
        self.ms_party_combo.currentIndexChanged.connect(self.on_party_selected)
        form_layout.addRow("MS Party (Stock Owner):", self.ms_party_combo)
        
        # From Party: Auto-set to "Universal Dyeing" and read-only
        self.from_party_input = QLineEdit()
        self.from_party_input.setText("UNIVERSAL DYEING")
        self.from_party_input.setReadOnly(True)
        self.from_party_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #888888;
            }
        """)
        form_layout.addRow("From Party:", self.from_party_input)
        
        # Transfer To field - different behavior for By Name Transfer
        if self.transfer_type == 'by_name':
            # For By Name Transfer: Use QComboBox with Liabilities master list
            self.transfer_to_combo = QComboBox()
            self.transfer_to_combo.setEditable(True)  # Allow typing for autocomplete
            self.transfer_to_combo.setStyleSheet(self.get_combo_style())
            self.transfer_to_combo.addItem("")  # Allow blank
            self.transfer_to_combo.lineEdit().textChanged.connect(self.auto_uppercase_text)
            form_layout.addRow("Transfer To (MS Party):", self.transfer_to_combo)
            self.transfer_to_input = None  # Not used for By Name Transfer
        else:
            # For Simple Transfer: Use QComboBox with Liabilities master list
            self.transfer_to_input = QComboBox()
            self.transfer_to_input.setEditable(True)
            self.transfer_to_input.setStyleSheet(self.get_combo_style())
            self.transfer_to_input.addItem("")  # Allow blank
            self.transfer_to_input.lineEdit().textChanged.connect(self.auto_uppercase_text)
            form_layout.addRow("Transfer To:", self.transfer_to_input)
            self.transfer_to_combo = None  # Not used for Simple Transfer
        
        # Vehicle / Driver fields:
        # - For SIMPLE transfers, show and allow entry.
        # - For BY NAME transfers, keep fields internal (for legacy data) but do not show them in the UI.
        self.vehicle_input = QLineEdit()
        self.driver_input = QLineEdit()
        if self.transfer_type != 'by_name':
            self.vehicle_input.setStyleSheet(self.get_input_style())
            self.vehicle_input.textChanged.connect(self.auto_uppercase_text)
            form_layout.addRow("Vehicle Number:", self.vehicle_input)
            
            self.driver_input.setStyleSheet(self.get_input_style())
            self.driver_input.textChanged.connect(self.auto_uppercase_text)
            form_layout.addRow("Driver Name:", self.driver_input)
        
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setStyleSheet(self.get_input_style())
        form_layout.addRow("Date:", self.date_input)
        
        layout.addLayout(form_layout)
        
        items_label = QLabel("Items (Select MS Party first to load available stock):")
        items_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(items_label)
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(4)
        self.items_table.setHorizontalHeaderLabels(["Item Name", "Measurement", "Available Stock", "Transfer Quantity"])
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        # Connect itemChanged to auto-uppercase item names
        self.items_table.itemChanged.connect(self.on_item_changed)
        self.items_table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                gridline-color: #3d3d3d;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                padding: 8px;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.items_table)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_transfer)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
        # Don't populate form here - wait for parties to load first
        # populate_form will be called from load_parties_with_stock when parties are ready
    
    def get_input_style(self):
        return """
            QLineEdit, QDateEdit {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
            }
            QLineEdit:focus, QDateEdit:focus {
                border: 2px solid #0078d4;
            }
        """
    
    def get_combo_style(self):
        return """
            QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
            }
            QComboBox:focus {
                border: 2px solid #0078d4;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #ffffff;
                selection-background-color: #0078d4;
            }
        """
    
    def load_parties_with_stock(self):
        try:
            print(f"[OutwardDialog] load_parties_with_stock: Starting, document={self.document is not None}")
            response = self.api_client._try_request("GET", "/api/stock/parties")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.parties_with_stock = data.get("parties", [])
                    print(f"[OutwardDialog] load_parties_with_stock: Loaded {len(self.parties_with_stock)} parties with stock")
                    for party in self.parties_with_stock:
                        self.ms_party_combo.addItem(party['name'], party['id'])
            
            # Load Liabilities master list for Transfer To fields (both Simple and By Name)
            self.liabilities_list = []
            try:
                parties_response = self.api_client._try_request("GET", "/api/parties")
                if parties_response and parties_response.status_code == 200:
                    parties_data = parties_response.json()
                    if parties_data.get("success"):
                        all_p = parties_data.get("parties", [])
                        self.liabilities_list = [p for p in all_p if p.get('is_active', True)]
                        liability_names = [p['name'] for p in self.liabilities_list]
                        
                        # Populate Transfer To combo for By Name Transfer
                        if hasattr(self, 'transfer_type') and self.transfer_type == 'by_name' and hasattr(self, 'transfer_to_combo') and self.transfer_to_combo:
                            for name in liability_names:
                                self.transfer_to_combo.addItem(name)
                        
                        # Populate Transfer To combo for Simple Transfer
                        if hasattr(self, 'transfer_to_input') and self.transfer_to_input:
                            for name in liability_names:
                                self.transfer_to_input.addItem(name)
                        
                        # Populate Outward To combo for OutwardDialog (avoid duplicates)
                        if hasattr(self, 'outward_to_input') and self.outward_to_input:
                            # Only add if combo is empty (to avoid duplicates from setup_autocomplete)
                            if self.outward_to_input.count() <= 1:  # Only has blank item
                                seen = set()
                                for name in liability_names:
                                    if name and name not in seen:
                                        self.outward_to_input.addItem(name)
                                        seen.add(name)
            except Exception as e:
                print(f"[TransferDialog] load_parties_with_stock: Error loading liabilities: {e}")
            
            # If editing, also fetch the MS Party from document even if it has no stock
            if self.document:
                ms_party_id = self.document.get('ms_party_id')
                print(f"[OutwardDialog] load_parties_with_stock: Document MS Party ID: {ms_party_id}")
                if ms_party_id:
                    # Check if party is already in the combo box
                    party_found = False
                    for i in range(self.ms_party_combo.count()):
                        if self.ms_party_combo.itemData(i) == ms_party_id:
                            party_found = True
                            print(f"[OutwardDialog] load_parties_with_stock: Party found in combo at index {i}")
                            break
                    
                    # If not found, fetch party info from API and add it
                    if not party_found:
                        print(f"[OutwardDialog] load_parties_with_stock: Party not found, fetching from API")
                        try:
                            parties_response = self.api_client._try_request("GET", "/api/parties")
                            if parties_response and parties_response.status_code == 200:
                                parties_data = parties_response.json()
                                if parties_data.get("success"):
                                    all_parties = parties_data.get("parties", [])
                                    party = next((p for p in all_parties if p['id'] == ms_party_id), None)
                                    if party:
                                        print(f"[OutwardDialog] load_parties_with_stock: Adding party {party['name']} to combo")
                                        self.ms_party_combo.addItem(party['name'], party['id'])
                        except Exception as e:
                            print(f"[OutwardDialog] load_parties_with_stock: Error fetching party: {e}")
                    
                    # Populate form after parties are loaded (with longer delay to ensure combo is ready)
                    from PyQt5.QtCore import QTimer
                    print(f"[OutwardDialog] load_parties_with_stock: Scheduling populate_form in 200ms")
                    QTimer.singleShot(200, lambda: self.populate_form())
        except Exception as e:
            print(f"[OutwardDialog] load_parties_with_stock: EXCEPTION: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
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
    
    def on_item_changed(self, item):
        """Handle item changes in table - auto-uppercase item names and validate quantities"""
        if item.column() == 0:  # Item Name column
            text = item.text()
            uppercase_text = text.upper()
            if text != uppercase_text:
                item.setText(uppercase_text)
        elif item.column() == 3:  # Quantity column (for both Transfer and Outward)
            # Validate quantity - must be positive
            try:
                quantity = float(item.text())
                if quantity < 0:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Invalid Quantity", 
                                      f"Quantity cannot be negative.\nPlease enter a positive value.")
                    # Reset to 0 or previous value
                    item.setText("0")
                elif quantity == 0:
                    # Allow 0 but warn if it was previously non-zero
                    pass
            except ValueError:
                # Not a valid number - allow user to continue typing
                pass
    
    def setup_autocomplete(self):
        """Set up autocomplete for Transfer To fields using Liabilities master list"""
        try:
            # Get Liabilities master list (if not already loaded)
            if not hasattr(self, 'liabilities_list') or not self.liabilities_list:
                response = self.api_client._try_request("GET", "/api/parties")
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        all_p = data.get("parties", [])
                        self.liabilities_list = [p for p in all_p if p.get('is_active', True)]
            
            if not hasattr(self, 'liabilities_list') or not self.liabilities_list:
                return
            
            liability_names = [p['name'] for p in self.liabilities_list]
            
            # For By Name Transfer, set up autocomplete for Transfer To combo box
            if self.transfer_type == 'by_name' and hasattr(self, 'transfer_to_combo') and self.transfer_to_combo:
                from PyQt5.QtWidgets import QCompleter
                from PyQt5.QtCore import Qt
                transfer_to_completer = QCompleter(liability_names, self.transfer_to_combo)
                transfer_to_completer.setCaseSensitivity(Qt.CaseInsensitive)
                transfer_to_completer.setCompletionMode(QCompleter.PopupCompletion)
                transfer_to_completer.setFilterMode(Qt.MatchContains)
                transfer_to_completer.setMaxVisibleItems(10)
                self.transfer_to_combo.setCompleter(transfer_to_completer)
                
                # Style the completer popup
                transfer_to_completer.popup().setStyleSheet("""
                    QListView {
                        background-color: #1e1e1e;
                        border: 1px solid #3d3d3d;
                        color: #ffffff;
                        selection-background-color: #0078d4;
                        selection-color: #ffffff;
                        padding: 2px;
                    }
                """)
            
            # Set up completer for Transfer To (Simple Transfer)
            if hasattr(self, 'transfer_to_input') and self.transfer_to_input:
                from PyQt5.QtWidgets import QCompleter
                from PyQt5.QtCore import Qt
                transfer_completer = QCompleter(liability_names, self.transfer_to_input)
                transfer_completer.setCaseSensitivity(Qt.CaseInsensitive)
                transfer_completer.setCompletionMode(QCompleter.PopupCompletion)
                transfer_completer.setFilterMode(Qt.MatchContains)
                transfer_completer.setMaxVisibleItems(10)
                self.transfer_to_input.setCompleter(transfer_completer)
                
                # Style the completer popup
                transfer_completer.popup().setStyleSheet("""
                    QListView {
                        background-color: #1e1e1e;
                        border: 1px solid #3d3d3d;
                        color: #ffffff;
                        selection-background-color: #0078d4;
                        selection-color: #ffffff;
                        padding: 2px;
                    }
                """)
        except Exception as e:
            print(f"Error setting up autocomplete: {e}")
            import traceback
            traceback.print_exc()
    
    def save_party_name_if_new(self, party_name):
        """Save party name to global parties table if it's new"""
        if not party_name or not party_name.strip():
            return
        
        party_name = party_name.strip()
        try:
            # Try to save the party name (API will handle if it already exists)
            response = requests.post(
                "/api/save-party-name",
                json={"party_name": party_name}
            )
            # Don't show error to user - just silently save if new
        except:
            pass  # Silently fail - user can still use the name
    
    def on_party_selected(self):
        """Load available stock when party is selected and populate items table"""
        party_id = self.ms_party_combo.currentData()
        if not party_id:
            # Clear table if no party selected
            self.items_table.setRowCount(0)
            return
        
        try:
            response = self.api_client._try_request("GET", f"/api/stock/{party_id}/available")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    stock_list = data.get("stock", [])
                    self.available_stock = {}
                    
                    # Build available_stock dict from API response
                    for item in stock_list:
                        key = (item['item_name'], item['measurement'])
                        self.available_stock[key] = item['remaining_stock']
                    
                    # If editing, merge document items with stock items
                    if self.document:
                        self.populate_items_merged_with_document(stock_list)
                    else:
                        # Not editing - just show available stock
                        self.items_table.setRowCount(len(stock_list))
                        
                        for row, item in enumerate(stock_list):
                            item_name = item['item_name']
                            measurement = item['measurement']
                            available = item['remaining_stock']
                            
                            # Item Name (read-only)
                            name_item = QTableWidgetItem(item_name)
                            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                            name_item.setBackground(Qt.darkGray)
                            self.items_table.setItem(row, 0, name_item)
                            
                            # Measurement (read-only)
                            measurement_item = QTableWidgetItem(str(measurement))
                            measurement_item.setFlags(measurement_item.flags() & ~Qt.ItemIsEditable)
                            measurement_item.setBackground(Qt.darkGray)
                            self.items_table.setItem(row, 1, measurement_item)
                            
                            # Available Stock (read-only)
                            stock_item = QTableWidgetItem(str(available))
                            stock_item.setFlags(stock_item.flags() & ~Qt.ItemIsEditable)
                            stock_item.setBackground(Qt.darkGray)
                            self.items_table.setItem(row, 2, stock_item)
                            
                            # Transfer Quantity (editable, default 0)
                            qty_item = QTableWidgetItem("0")
                            self.items_table.setItem(row, 3, qty_item)
        except Exception as e:
            # If error and we're editing, try to populate from document
            if self.document:
                self.populate_items_from_document()
            else:
                QMessageBox.warning(self, "Error", f"Failed to load stock: {str(e)}")
    
    def populate_items_merged_with_document(self, stock_list):
        """Populate items table merging document items with available stock"""
        if not self.document:
            return
        
        doc_items = self.document.get('items', [])
        if not doc_items:
            return
        
        # Create a set of stock keys for quick lookup
        stock_keys = {(item['item_name'], item['measurement']) for item in stock_list}
        
        # Build combined list: all document items, with stock data if available
        combined_items = []
        for doc_item in doc_items:
            item_name = doc_item.get('item_name', '')
            measurement = doc_item.get('measurement', 15)
            key = (item_name, measurement)
            
            # Find matching stock item
            stock_item = next((s for s in stock_list if (s['item_name'], s['measurement']) == key), None)
            available = stock_item['remaining_stock'] if stock_item else 0.0
            
            # Store in available_stock dict (even if 0)
            self.available_stock[key] = available
            
            combined_items.append({
                'item_name': item_name,
                'measurement': measurement,
                'available': available,
                'quantity': doc_item.get('quantity', 0)
            })
        
        # Populate table with all document items
        self.items_table.setRowCount(len(combined_items))
        
        for row, item in enumerate(combined_items):
            item_name = item['item_name']
            measurement = item['measurement']
            available = item['available']
            quantity = item['quantity']
            
            # Item Name (read-only)
            name_item = QTableWidgetItem(item_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setBackground(Qt.darkGray)
            self.items_table.setItem(row, 0, name_item)
            
            # Measurement (read-only)
            measurement_item = QTableWidgetItem(str(measurement))
            measurement_item.setFlags(measurement_item.flags() & ~Qt.ItemIsEditable)
            measurement_item.setBackground(Qt.darkGray)
            self.items_table.setItem(row, 1, measurement_item)
            
            # Available Stock (read-only)
            stock_item = QTableWidgetItem(str(available))
            stock_item.setFlags(stock_item.flags() & ~Qt.ItemIsEditable)
            stock_item.setBackground(Qt.darkGray)
            self.items_table.setItem(row, 2, stock_item)
            
            # Transfer/Outward Quantity (editable, set from document)
            qty_item = QTableWidgetItem(str(quantity))
            self.items_table.setItem(row, 3, qty_item)
        
        # Store original quantities for validation
        self.original_document_quantities = {}
        for doc_item in doc_items:
            key = (doc_item.get('item_name', ''), doc_item.get('measurement', 15))
            self.original_document_quantities[key] = doc_item.get('quantity', 0)
    
    def populate_items_from_document(self):
        """Populate items table from document items when party has no stock"""
        if not self.document:
            return
        
        items = self.document.get('items', [])
        if not items:
            return
        
        self.available_stock = {}
        self.items_table.setRowCount(len(items))
        
        for row, item in enumerate(items):
            item_name = item.get('item_name', '')
            measurement = item.get('measurement', 15)
            quantity = item.get('quantity', 0)
            
            # Store in available_stock dict (set to 0 since no stock available)
            key = (item_name, measurement)
            self.available_stock[key] = 0
            
            # Item Name (read-only)
            name_item = QTableWidgetItem(item_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setBackground(Qt.darkGray)
            self.items_table.setItem(row, 0, name_item)
            
            # Measurement (read-only)
            measurement_item = QTableWidgetItem(str(measurement))
            measurement_item.setFlags(measurement_item.flags() & ~Qt.ItemIsEditable)
            measurement_item.setBackground(Qt.darkGray)
            self.items_table.setItem(row, 1, measurement_item)
            
            # Available Stock (read-only, show 0)
            stock_item = QTableWidgetItem("0")
            stock_item.setFlags(stock_item.flags() & ~Qt.ItemIsEditable)
            stock_item.setBackground(Qt.darkGray)
            self.items_table.setItem(row, 2, stock_item)
            
            # Transfer Quantity (editable, set from document)
            qty_item = QTableWidgetItem(str(quantity))
            self.items_table.setItem(row, 3, qty_item)
        
        # Store original quantities
        self.original_document_quantities = {}
        for item in items:
            key = (item.get('item_name', ''), item.get('measurement', 15))
            self.original_document_quantities[key] = item.get('quantity', 0)
    
    def populate_form(self):
        """Populate form when editing existing document"""
        if not self.document:
            return
        
        # Fill in other fields first
        # From Party: Always set to "Universal Dyeing" (read-only)
        self.from_party_input.setText("UNIVERSAL DYEING")
        
        # Handle Transfer To field based on transfer type
        if self.transfer_type == 'by_name' and self.transfer_to_combo:
            # For By Name Transfer: Set liability name from document
            transfer_to_name = self.document.get('transfer_to', '')
            if transfer_to_name:
                index = self.transfer_to_combo.findText(transfer_to_name)
                if index >= 0:
                    self.transfer_to_combo.setCurrentIndex(index)
                else:
                    # If not found (legacy data), add temporarily
                    self.transfer_to_combo.addItem(transfer_to_name)
                    self.transfer_to_combo.setCurrentText(transfer_to_name)
        elif hasattr(self, 'transfer_to_input') and self.transfer_to_input:
            # For Simple Transfer: Set liability name
            transfer_to_name = self.document.get('transfer_to', '')
            if transfer_to_name:
                index = self.transfer_to_input.findText(transfer_to_name)
                if index >= 0:
                    self.transfer_to_input.setCurrentIndex(index)
                else:
                    # If not found (legacy data), add temporarily
                    self.transfer_to_input.addItem(transfer_to_name)
                    self.transfer_to_input.setCurrentText(transfer_to_name)
        
        self.vehicle_input.setText(self.document.get('vehicle_number', ''))
        self.driver_input.setText(self.document.get('driver_name', ''))
        
        date_str = self.document.get('document_date', '')
        if date_str:
            try:
                date = QDate.fromString(date_str[:10], "yyyy-MM-dd")
                self.date_input.setDate(date)
            except:
                pass
        
        # Set MS Party last (this will trigger on_party_selected and populate stock)
        # Temporarily disconnect to avoid triggering during setup
        try:
            self.ms_party_combo.currentIndexChanged.disconnect()
        except TypeError:
            pass  # Not connected yet
        
        ms_party_id = self.document.get('ms_party_id')
        party_found = False
        for i in range(self.ms_party_combo.count()):
            if self.ms_party_combo.itemData(i) == ms_party_id:
                self.ms_party_combo.setCurrentIndex(i)
                party_found = True
                break
        
        # Reconnect signal
        self.ms_party_combo.currentIndexChanged.connect(self.on_party_selected)
        
        # If party was found, manually trigger stock loading
        if party_found:
            self.on_party_selected()
        else:
            # Party not found - try to set it anyway (might have been added by load_parties_with_stock)
            # Try one more time to find it
            for i in range(self.ms_party_combo.count()):
                if self.ms_party_combo.itemData(i) == ms_party_id:
                    self.ms_party_combo.setCurrentIndex(i)
                    self.on_party_selected()
                    return
    
    def update_quantities_from_document(self):
        """Update quantities in table from document items (called after stock loads)"""
        if not self.document:
            return
        
        items = self.document.get('items', [])
        # Create a dict for quick lookup and store original quantities
        doc_items = {}
        self.original_document_quantities = {}
        for item in items:
            key = (item.get('item_name', ''), item.get('measurement', 15))
            qty = item.get('quantity', 0)
            doc_items[key] = qty
            self.original_document_quantities[key] = qty
        
        # Update quantities in table
        for row in range(self.items_table.rowCount()):
            name_item = self.items_table.item(row, 0)
            measurement_item = self.items_table.item(row, 1)
            qty_item = self.items_table.item(row, 3)
            
            if name_item and measurement_item and qty_item:
                item_name = name_item.text()
                measurement = int(measurement_item.text())
                key = (item_name, measurement)
                
                if key in doc_items:
                    qty_item.setText(str(doc_items[key]))
    
    # Removed add_item_row and remove_item_row - items are auto-populated from stock
    
    def save_transfer(self):
        ms_party_id = self.ms_party_combo.currentData()
        if not ms_party_id:
            QMessageBox.warning(self, "Validation", "Please select MS Party")
            return
        
        items = []
        for row in range(self.items_table.rowCount()):
            item_name = self.items_table.item(row, 0)
            measurement_item = self.items_table.item(row, 1)
            available_stock_item = self.items_table.item(row, 2)
            quantity_item = self.items_table.item(row, 3)
            
            if not item_name or not item_name.text().strip():
                continue
            
            item_name_str = item_name.text().strip()
            measurement = int(measurement_item.text())
            available = float(available_stock_item.text() if available_stock_item else 0)
            quantity = float(quantity_item.text() if quantity_item else 0)
            
            # Only include items with quantity > 0
            if quantity <= 0:
                continue
            
            # When editing, calculate temp_check = available_stock + original_transfer_quantity
            # This allows editing up to the original quantity + what's currently available
            # Example: available=400, original_transfer=200, temp_check=600, user can edit up to 600
            key = (item_name_str, measurement)
            if self.document and key in self.original_document_quantities:
                original_qty = self.original_document_quantities[key]
                temp_check = original_qty + available
                if quantity > temp_check:
                    QMessageBox.warning(self, "Validation", 
                        f"Quantity exceeds available stock for {item_name_str} ({measurement}).\n"
                        f"Available stock: {available}, Original transfer quantity: {original_qty}\n"
                        f"Maximum allowed: {temp_check}, Requested: {quantity}")
                    return
            else:
                # New item (not in original document) - just check against available stock
                if quantity > available:
                    QMessageBox.warning(self, "Validation", 
                        f"Insufficient stock for {item_name_str} ({measurement}). Available: {available}, Requested: {quantity}")
                    return
            
            items.append({
                "item_name": item_name_str,
                "measurement": measurement,
                "quantity": quantity
            })
        
        if not items:
            QMessageBox.warning(self, "Validation", "Please enter transfer quantity for at least one item")
            return
        
        # From Party: Always "Universal Dyeing"
        from_party_name = "UNIVERSAL DYEING"
        
        # Handle Transfer To field based on transfer type
        transfer_to_name = ""
        transfer_to_ms_party_id = None
        
        # Get valid liability names for validation
        valid_names = [p.get("name", "") for p in (getattr(self, 'liabilities_list', []) or [])]
        valid_map = {p.get("name", ""): p.get("id") for p in (getattr(self, 'liabilities_list', []) or [])}
        
        if self.transfer_type == 'by_name':
            # For By Name Transfer: Validate against Liabilities master
            transfer_to_name = self.transfer_to_combo.currentText().strip()
            if transfer_to_name:
                if transfer_to_name not in valid_names:
                    QMessageBox.warning(
                        self,
                        "Validation",
                        "Transfer To must be selected from Liabilities master list.",
                    )
                    return
                transfer_to_ms_party_id = valid_map.get(transfer_to_name)
                
                # Validate: Transfer To MS Party cannot be same as source MS Party
                if transfer_to_ms_party_id == ms_party_id:
                    QMessageBox.warning(self, "Validation", 
                        "Transfer To MS Party cannot be the same as source MS Party (Stock Owner)")
                    return
        else:
            # For Simple Transfer: Validate against Liabilities master
            if hasattr(self, 'transfer_to_input') and self.transfer_to_input:
                transfer_to_name = self.transfer_to_input.currentText().strip()
                if transfer_to_name:
                    if transfer_to_name not in valid_names:
                        QMessageBox.warning(
                            self,
                            "Validation",
                            "Transfer To must be selected from Liabilities master list.",
                        )
                        return
        
        data = {
            "ms_party_id": ms_party_id,
            "from_party": from_party_name,
            "transfer_to": transfer_to_name,
            "transfer_to_ms_party_id": transfer_to_ms_party_id,
            "transfer_type": self.transfer_type,
            "vehicle_number": self.vehicle_input.text(),
            "driver_name": self.driver_input.text(),
            "document_date": self.date_input.date().toString("yyyy-MM-dd"),
            "items": items,
            "created_by": self.user_data.get('username', 'Unknown') if self.user_data else 'Unknown'
        }
        
        try:
            if self.document:
                data["transfer_id"] = self.document['id']
                response = self.api_client._try_request_with_retry("PUT", "/api/transfer", json=data)
            else:
                response = self.api_client._try_request_with_retry("POST", "/api/transfer", json=data)
            
            if response and response.status_code in [200, 201]:
                result = response.json()
                if result.get("success"):
                    QMessageBox.information(self, "Success", "Document saved successfully")
                    if isinstance(result.get("document"), dict):
                        self.saved_document = result.get("document")
                    self.accept()
                else:
                    QMessageBox.warning(self, "Error", result.get("message", "Failed to save"))
            elif response is None:
                # Connection failed after all retries
                QMessageBox.warning(
                    self, "Connection Error",
                    "Unable to connect to the server after multiple attempts.\n\n"
                    "Please check your network connection and try again.\n"
                    "Your data has been preserved in the form."
                )
            else:
                error_msg = "Unknown error"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", error_msg)
                except:
                    pass
                QMessageBox.warning(self, "Error", f"Server error: {error_msg}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")


# ==================== OUTWARD MODULE ====================
# Similar to Transfer, but with "Outward To" instead of "Transfer To"
# Implementation would be nearly identical to TransferModule/TransferDialog
# For brevity, I'll create a simplified version

class OutwardModule(TransferModule):
    """Outward Data Entry Module (similar to Transfer)"""
    
    def __init__(self, parent=None, user_data=None):
        QWidget.__init__(self, parent)
        self.user_data = user_data
        self.server_available = True
        self.ws_bus = (user_data or {}).get("ws_bus")
        self.api_client = APIClient()
        # Set username on API client for edited_by tracking
        if user_data and user_data.get('username'):
            self.api_client.set_username(user_data.get('username'))
        self._data_loaded = False  # Track if data has been loaded
        self._setup_realtime("outward")
        self.init_ui()
        # Don't load data immediately - wait until module is shown
    
    def load_data_if_needed(self):
        """Load data if not already loaded (called explicitly when module is shown)"""
        if not self._data_loaded:
            self._data_loaded = True
            self.load_documents_async()
    
    def showEvent(self, event):
        """Handle show event (but don't load here - use load_data_if_needed instead)"""
        super().showEvent(event)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        header = QHBoxLayout()
        title = QLabel("📤 Outward Documents")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)
        header.addStretch()
        
        self.add_btn = QPushButton("➕ Add Outward")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.add_btn.clicked.connect(self.add_outward)
        header.addWidget(self.add_btn)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        self.refresh_btn.clicked.connect(self.load_documents_async)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # Filter Bar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        # MS Party Filter
        ms_party_label = QLabel("MS Party:")
        ms_party_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        filter_layout.addWidget(ms_party_label)
        
        self.ms_party_filter = QLineEdit()
        self.ms_party_filter.setPlaceholderText("Filter by MS Party...")
        self.ms_party_filter.setStyleSheet("""
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
        self.ms_party_filter.textChanged.connect(self.filter_table)
        filter_layout.addWidget(self.ms_party_filter)
        
        # GP # Filter
        gp_label = QLabel("GP #:")
        gp_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        filter_layout.addWidget(gp_label)
        
        self.gp_filter = QLineEdit()
        self.gp_filter.setPlaceholderText("Filter by GP #...")
        self.gp_filter.setStyleSheet("""
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
        self.gp_filter.textChanged.connect(self.filter_table)
        self.gp_filter.textChanged.connect(self.auto_uppercase_text)
        filter_layout.addWidget(self.gp_filter)
        
        # OUTWARD # Filter
        outward_label = QLabel("OUTWARD #:")
        outward_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        filter_layout.addWidget(outward_label)
        
        self.outward_filter = QLineEdit()
        self.outward_filter.setPlaceholderText("Filter by OUTWARD #...")
        self.outward_filter.setStyleSheet("""
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
        self.outward_filter.textChanged.connect(self.filter_table)
        self.outward_filter.textChanged.connect(self.auto_uppercase_text)
        filter_layout.addWidget(self.outward_filter)
        
        # Date range filters
        date_label = QLabel("From:")
        date_label.setStyleSheet("color: #ffffff;")
        filter_layout.addWidget(date_label)
        
        self.from_date_input = QDateEdit()
        self.from_date_input.setDate(QDate(2000, 1, 1))
        self.from_date_input.setCalendarPopup(True)
        self.from_date_input.setStyleSheet("""
            QDateEdit {
                background-color: #2a2a2a;
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
            }
            QDateEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        self.from_date_input.dateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.from_date_input)
        
        to_label = QLabel("To:")
        to_label.setStyleSheet("color: #ffffff;")
        filter_layout.addWidget(to_label)
        
        self.to_date_input = QDateEdit()
        self.to_date_input.setDate(QDate(2099, 12, 31))
        self.to_date_input.setCalendarPopup(True)
        self.to_date_input.setStyleSheet("""
            QDateEdit {
                background-color: #2a2a2a;
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
            }
            QDateEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        self.to_date_input.dateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.to_date_input)
        
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
        filter_layout.addWidget(clear_btn)
        
        layout.addLayout(filter_layout)
        
        # Setup autocomplete for MS Party filter
        self.setup_ms_party_autocomplete()
        
        # Store original documents for filtering
        self.all_documents = []
        
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "OUTWARD #", "GP #", "SR #", "MS Party", "From Party",
            "Outward To", "Vehicle #", "Driver", "Total Qty", "Date"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #252525;
                border: 1px solid #3d3d3d;
                gridline-color: #3d3d3d;
                color: #ffffff;
            }
            QTableWidget::item {
                padding: 5px;
                background-color: #1e1e1e;
            }
            QTableWidget::item:alternate {
                background-color: #252525;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QTableWidget::item:selected:alternate {
                background-color: #0078d4;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                padding: 8px;
                border: none;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.edit_selected_outward)
        # Set column widths - give more space to "Outward To" column (index 5)
        self.table.setColumnWidth(5, 180)  # Outward To column
        layout.addWidget(self.table)
        
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.clicked.connect(self.edit_selected_outward)
        self.edit_btn.setEnabled(False)
        action_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self.delete_selected_outward)
        self.delete_btn.setEnabled(False)
        action_layout.addWidget(self.delete_btn)
        
        self.print_btn = QPushButton("🖨️ Print")
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #107c10;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0d5f0d;
            }
        """)
        self.print_btn.clicked.connect(self.print_outwards)
        action_layout.addWidget(self.print_btn)
        
        layout.addLayout(action_layout)
        
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        self.setLayout(layout)
    
    def on_selection_changed(self):
        has_selection = len(self.table.selectedItems()) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def load_documents_async(self):
        self.loader = DocumentLoader("outward")
        self.loader.finished.connect(self.populate_table)
        self.loader.error.connect(self.on_load_error)
        self.loader.start()
    
    def populate_table(self, documents):
        """Populate table with documents"""
        # Store all documents for filtering
        self.all_documents = documents
        self.filter_table()
    
    def setup_ms_party_autocomplete(self):
        """Set up autocomplete for MS Party filter"""
        try:
            # Get MS parties only (from party management module)
            response = self.api_client._try_request("GET", "/api/parties")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    parties = data.get("parties", [])
                    active_parties = [p for p in parties if p.get('is_active', True)]
                    party_names = [party['name'] for party in active_parties]
                    
                    from PyQt5.QtWidgets import QCompleter
                    from PyQt5.QtCore import Qt
                    completer = QCompleter(party_names, self.ms_party_filter)
                    completer.setCaseSensitivity(Qt.CaseInsensitive)
                    completer.setCompletionMode(QCompleter.PopupCompletion)
                    completer.setFilterMode(Qt.MatchContains)
                    completer.setMaxVisibleItems(10)
                    self.ms_party_filter.setCompleter(completer)
                    
                    # Style the completer popup
                    completer.popup().setStyleSheet("""
                        QListView {
                            background-color: #1e1e1e;
                            border: 1px solid #3d3d3d;
                            color: #ffffff;
                            selection-background-color: #0078d4;
                            selection-color: #ffffff;
                            padding: 2px;
                        }
                    """)
        except:
            pass
    
    def auto_uppercase_text(self, text):
        """Automatically convert text to uppercase as user types (except MS Party filter)"""
        sender = self.sender()
        if sender and sender != self.ms_party_filter:  # Don't uppercase MS Party filter (for autocomplete)
            cursor_pos = sender.cursorPosition()
            uppercase_text = text.upper()
            if text != uppercase_text:
                sender.blockSignals(True)
                sender.setText(uppercase_text)
                sender.setCursorPosition(min(cursor_pos, len(uppercase_text)))
                sender.blockSignals(False)
    
    def filter_table(self):
        """Filter table based on search criteria"""
        # Safety check: ensure widget still exists
        if not hasattr(self, 'table') or self.table is None:
            return
        try:
            _ = self.table.objectName()
        except RuntimeError:
            # Widget was deleted
            return
        
        if not hasattr(self, 'all_documents'):
            self.all_documents = []
        
        # If all_documents is empty, clear the table
        if not self.all_documents:
            try:
                self.table.setRowCount(0)
            except RuntimeError:
                pass
            return
        
        # Get filter values
        ms_party_filter = ""
        gp_filter = ""
        outward_filter = ""
        from_date = QDate(2000, 1, 1)
        to_date = QDate(2099, 12, 31)
        
        try:
            if hasattr(self, 'ms_party_filter') and self.ms_party_filter is not None:
                ms_party_filter = self.ms_party_filter.text().upper()
            if hasattr(self, 'gp_filter') and self.gp_filter is not None:
                gp_filter = self.gp_filter.text().upper()
            if hasattr(self, 'outward_filter') and self.outward_filter is not None:
                outward_filter = self.outward_filter.text().upper()
            if hasattr(self, 'from_date_input') and self.from_date_input is not None:
                from_date = self.from_date_input.date()
            if hasattr(self, 'to_date_input') and self.to_date_input is not None:
                to_date = self.to_date_input.date()
        except RuntimeError:
            # Widgets were deleted
            pass
        
        filtered_docs = []
        for doc in self.all_documents:
            # Check MS Party filter
            matches_ms_party = True
            if ms_party_filter:
                ms_party = doc.get('ms_party_name', '').upper()
                matches_ms_party = ms_party_filter in ms_party
            
            # Check GP # filter
            matches_gp = True
            if gp_filter:
                gp_num = doc.get('gp_number', '').upper()
                matches_gp = gp_filter in gp_num
            
            # Check OUTWARD # filter
            matches_outward = True
            if outward_filter:
                outward_num = doc.get('outward_number', '').upper()
                matches_outward = outward_filter in outward_num
            
            # Check date range
            matches_date = True
            doc_date_str = doc.get('document_date', '')
            if doc_date_str:
                try:
                    doc_date = QDate.fromString(doc_date_str[:10], "yyyy-MM-dd")
                    matches_date = from_date <= doc_date <= to_date
                except:
                    matches_date = True
            
            # All filters must match (AND logic)
            if matches_ms_party and matches_gp and matches_outward and matches_date:
                filtered_docs.append(doc)
        
        # Populate table with filtered documents
        try:
            self.table.setRowCount(len(filtered_docs))
            for row, doc in enumerate(filtered_docs):
                self.table.setItem(row, 0, QTableWidgetItem(doc.get('outward_number', '')))
                self.table.setItem(row, 1, QTableWidgetItem(doc.get('gp_number', '')))
                self.table.setItem(row, 2, QTableWidgetItem(doc.get('sr_number', '')))
                self.table.setItem(row, 3, QTableWidgetItem(doc.get('ms_party_name', '')))
                self.table.setItem(row, 4, QTableWidgetItem(doc.get('from_party', '')))
                self.table.setItem(row, 5, QTableWidgetItem(doc.get('outward_to', '')))
                self.table.setItem(row, 6, QTableWidgetItem(doc.get('vehicle_number', '')))
                self.table.setItem(row, 7, QTableWidgetItem(doc.get('driver_name', '')))
                self.table.setItem(row, 8, QTableWidgetItem(str(doc.get('total_quantity', 0))))
                date_str = doc.get('document_date', '')
                if date_str:
                    date_str = date_str[:10]
                self.table.setItem(row, 9, QTableWidgetItem(date_str))
                self.table.item(row, 0).setData(Qt.UserRole, doc.get('id'))
        except RuntimeError:
            # Widget was deleted during operation
            pass
    
    def clear_search(self):
        """Clear all search filters"""
        if hasattr(self, 'ms_party_filter'):
            self.ms_party_filter.clear()
        if hasattr(self, 'gp_filter'):
            self.gp_filter.clear()
        if hasattr(self, 'outward_filter'):
            self.outward_filter.clear()
        if hasattr(self, 'from_date_input'):
            self.from_date_input.setDate(QDate(2000, 1, 1))
        if hasattr(self, 'to_date_input'):
            self.to_date_input.setDate(QDate(2099, 12, 31))
        if hasattr(self, 'all_documents'):
            self.filter_table()
    
    def on_load_error(self, error):
        QMessageBox.warning(self, "Error", f"Failed to load documents: {error}")
        self.server_available = False
    
    def add_outward(self):
        if not self.server_available:
            QMessageBox.warning(self, "Server Offline", "Server is not available.")
            return
        
        # Show party search dialog first
        party_dialog = PartySearchDialog(self)
        if party_dialog.exec_() == QDialog.Accepted and party_dialog.selected_party:
            # Open outward dialog with pre-selected party
            dialog = OutwardDialog(self, user_data=self.user_data, preselected_party=party_dialog.selected_party)
            if dialog.exec_() == QDialog.Accepted:
                saved = getattr(dialog, "saved_document", None)
                if isinstance(saved, dict) and saved.get("id"):
                    self._upsert_document(saved, prefer_top=True)
                else:
                    self.load_documents_async()
    
    def edit_selected_outward(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        doc_id = self.table.item(row, 0).data(Qt.UserRole)
        
        try:
            response = self.api_client._try_request("GET", f"/api/outward/{doc_id}")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    document = data.get("document")
                    print(f"[OutwardModule] edit_selected_outward: Loaded document - ID: {document.get('id')}, MS Party ID: {document.get('ms_party_id')}")
                    print(f"[OutwardModule] Document fields: from_party={document.get('from_party')}, outward_to={document.get('outward_to')}")
                    dialog = OutwardDialog(self, document=document, user_data=self.user_data)
                    if dialog.exec_() == QDialog.Accepted:
                        saved = getattr(dialog, "saved_document", None)
                        if isinstance(saved, dict) and saved.get("id"):
                            self._upsert_document(saved, prefer_top=False)
                        else:
                            self.load_documents_async()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load document: {str(e)}")
    
    def delete_selected_outward(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        doc_id = self.table.item(row, 0).data(Qt.UserRole)
        doc_number = self.table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {doc_number}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                response = self.api_client._try_request_with_retry("DELETE", f"/api/outward/{doc_id}")
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        QMessageBox.information(self, "Success", "Document deleted successfully")
                        self._remove_document_by_id(doc_id)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")
    
    def print_outwards(self):
        """Show print dialog and print selected outwards"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one outward document to print")
            return
        
        dialog = PrintOutwardDialog(self, selected_rows, self.all_documents)
        if dialog.exec_() == QDialog.Accepted:
            selected_ids = dialog.get_selected_ids()
            if selected_ids:
                self.generate_and_print_html(selected_ids)
    
    def generate_and_print_html(self, outward_ids):
        """Generate HTML for printing and open in Chrome"""
        try:
            outwards = []
            for outward_id in outward_ids:
                response = self.api_client._try_request("GET", f"/api/outward/{outward_id}")
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        outwards.append(data.get("document"))
            
            if not outwards:
                QMessageBox.warning(self, "Error", "No outward documents found to print")
                return
            
            html_content = self.generate_print_html(outwards)
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME', ''))
            ]
            
            chrome_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
            
            if chrome_path:
                import subprocess
                # Open in new tab instead of new window
                subprocess.Popen([chrome_path, '--new-tab', 'file://' + temp_file.name.replace('\\', '/')])
            else:
                webbrowser.open('file://' + temp_file.name)
                QMessageBox.information(
                    self, "Print", 
                    "Print dialog opened. Please use Ctrl+P or File > Print to print the document."
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate print document: {str(e)}")
    
    def generate_print_html(self, outwards):
        """Generate print-ready HTML for outward documents"""
        html = self._get_base_html_styles()
        
        pages = []
        for i in range(0, len(outwards), 2):
            page_outwards = outwards[i:i+2]
            pages.append(page_outwards)
        
        for page_idx, page_outwards in enumerate(pages):
            html += '<div class="page">\n'
            
            for form_idx, outward in enumerate(page_outwards):
                html += self.generate_outward_form_html(outward)
                
                if form_idx < len(page_outwards) - 1:
                    html += '<div class="cut-line"></div>\n'
            
            html += '</div>\n'
        
        html += """
    <script>
        window.onload = function() {
            window.print();
        };
    </script>
</body>
</html>
"""
        return html
    
    def generate_outward_form_html(self, outward):
        """Generate HTML for a single outward form"""
        items = outward.get('items', [])
        
        doc_date = outward.get('document_date', '')
        if doc_date:
            try:
                date_obj = datetime.strptime(doc_date[:10], '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d-%m-%Y')
            except:
                formatted_date = doc_date[:10]
        else:
            formatted_date = ''
        
        logo_path = self.find_logo_file()
        logo_html = ''
        if logo_path:
            try:
                with open(logo_path, 'rb') as logo_file:
                    logo_data = logo_file.read()
                    logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                    logo_ext = os.path.splitext(logo_path)[1].lower()
                    mime_type = 'image/png' if logo_ext == '.png' else 'image/jpeg' if logo_ext in ['.jpg', '.jpeg'] else 'image/svg+xml' if logo_ext == '.svg' else 'image/png'
                    logo_html = f'<img src="data:{mime_type};base64,{logo_base64}" alt="Logo" style="background: transparent; width: 100%; height: 100%; object-fit: contain;" />'
            except:
                logo_html = f'<img src="{logo_path}" alt="Logo" style="background: transparent; width: 100%; height: 100%; object-fit: contain;" />'
        else:
            logo_html = '<div style="width: 100%; height: 100%; background: transparent; border: 1px dashed #ccc; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #999;">LOGO</div>'
        
        html = f"""
    <div class="form">
        <div class="header">
            <div class="logo">{logo_html}</div>
            <div class="company-name">MOMINA LACE DYEING</div>
            <div class="owner-info">
                Owner : GHULAM MUSTAFA<br>
                GM    : Shahid, Naveed
            </div>
        </div>
        
        <div class="subtitle">GOODS OUTWARD</div>
        
        <div class="meta-info">
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">SR# :</span>
                    <span class="meta-value">{outward.get('sr_number', '')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">DATE :</span>
                    <span class="meta-value">{formatted_date}</span>
                </div>
            </div>
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">MS PARTY :</span>
                    <span class="meta-value">{outward.get('ms_party_name', '')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">FROM :</span>
                    <span class="meta-value">{outward.get('from_party', '')}</span>
                </div>
            </div>
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">OUTWARD TO :</span>
                    <span class="meta-value">{outward.get('outward_to', '')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">VEHICLE NO :</span>
                    <span class="meta-value">{outward.get('vehicle_number', '')}</span>
                </div>
            </div>
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">DRIVER :</span>
                    <span class="meta-value">{outward.get('driver_name', '')}</span>
                </div>
                <div class="meta-item">
                </div>
            </div>
        </div>
        
        <table class="items-table">
            <thead>
                <tr>
                    <th style="width: 20%;">QTY (Than)</th>
                    <th style="width: 50%;">DETAILS (Item Name)</th>
                    <th style="width: 30%;">YARDS</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for item in items:
            qty = item.get('quantity', 0)
            item_name = item.get('item_name', '')
            measurement = item.get('measurement', '')
            html += f"""
                <tr>
                    <td>{qty}</td>
                    <td>{item_name}</td>
                    <td>{measurement}</td>
                </tr>
"""
        
        empty_rows = max(0, 3 - len(items))
        for _ in range(empty_rows):
            html += """
                <tr>
                    <td></td>
                    <td></td>
                    <td></td>
                </tr>
"""
        
        html += f"""
            </tbody>
        </table>
        
        <div class="footer">
            <div class="footer-row">
                <span class="footer-label">CREATED BY :</span>
                <span class="footer-value">{outward.get('created_by', '')}</span>
            </div>
            <div class="footer-row">
                <span class="footer-label">EDITED BY :</span>
                <span class="footer-value">{outward.get('edited_by', 'None') if outward.get('edited_by') else 'None'}</span>
            </div>
            {('' if not outward.get('edit_log_history') else f'<div class="footer-row"><span class="footer-label">EDIT LOG HISTORY :</span><span class="footer-value" style="font-size: 10px;">{outward.get("edit_log_history", "None")}</span></div>')}
            <div class="site-info">
                SITE:<br>
                Small Industrial State, Sargodha Road, Faisalabad
            </div>
            <div class="contacts">
                CONTACTS:<br>
                0321-7651815, 0300-8651815<br>
                0304-6166663, 0300-8636129
            </div>
        </div>
    </div>
"""
        return html


class PrintOutwardDialog(QDialog):
    """Dialog for selecting outwards to print"""
    
    def __init__(self, parent=None, selected_rows=None, all_documents=None):
        super().__init__(parent)
        self.selected_ids = []
        self.all_documents = all_documents or []
        self.selected_rows = selected_rows or set()
        self.setWindowTitle("Print Outward Documents")
        self.setMinimumSize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        instructions = QLabel("Select outward documents to print:")
        instructions.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        layout.addWidget(instructions)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        
        for idx, doc in enumerate(self.all_documents):
            item_text = f"{doc.get('outward_number', '')} - {doc.get('ms_party_name', '')} - {doc.get('document_date', '')[:10]}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, doc.get('id'))
            
            if idx in self.selected_rows:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            self.list_widget.addItem(item)
        
        layout.addWidget(self.list_widget)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        deselect_all_btn.clicked.connect(self.deselect_all)
        button_layout.addWidget(deselect_all_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
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
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        print_btn = QPushButton("Print")
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #107c10;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0d5f0d;
            }
        """)
        print_btn.clicked.connect(self.accept)
        button_layout.addWidget(print_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def select_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Checked)
    
    def deselect_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Unchecked)
    
    def get_selected_ids(self):
        selected_ids = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                outward_id = item.data(Qt.UserRole)
                if outward_id:
                    selected_ids.append(outward_id)
        return selected_ids


class OutwardDialog(TransferDialog):
    """Dialog for adding/editing outward document (similar to Transfer)"""
    
    def __init__(self, parent=None, document=None, user_data=None, preselected_party=None):
        QDialog.__init__(self, parent)
        self.document = document
        self.user_data = user_data
        self.saved_document = None  # returned by server for instant UI patching
        self.preselected_party = preselected_party
        self.parties_with_stock = []
        self.available_stock = {}
        self.original_document_quantities = {}  # Store original quantities when editing
        self.api_client = APIClient()
        # Set username on API client for edited_by tracking
        if user_data and user_data.get('username'):
            self.api_client.set_username(user_data.get('username'))
        self.setWindowTitle("Edit Outward" if document else "Add Outward")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        self.init_ui()
        
        # Debug logging
        if document:
            print(f"[OutwardDialog] __init__: Document provided - ID: {document.get('id')}, MS Party ID: {document.get('ms_party_id')}")
            print(f"[OutwardDialog] Document fields: from_party={document.get('from_party')}, outward_to={document.get('outward_to')}")
        else:
            print(f"[OutwardDialog] __init__: No document provided (adding new)")
        
        self.load_parties_with_stock()
        
        # Set up autocomplete after a short delay to ensure UI is fully initialized
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.setup_autocomplete)
        
        # If party was pre-selected, set it and load stock
        if self.preselected_party and not self.document:
            party_id = self.preselected_party.get('id')
            for i in range(self.ms_party_combo.count()):
                if self.ms_party_combo.itemData(i) == party_id:
                    self.ms_party_combo.setCurrentIndex(i)
                    break
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.ms_party_combo = QComboBox()
        self.ms_party_combo.setEditable(False)  # Not editable, must select from dropdown
        self.ms_party_combo.setStyleSheet(self.get_combo_style())
        self.ms_party_combo.addItem("-- Select MS Party --", None)  # Default option
        self.ms_party_combo.currentIndexChanged.connect(self.on_party_selected)
        form_layout.addRow("MS Party (Stock Owner):", self.ms_party_combo)
        
        # From Party: Auto-set to "Universal Dyeing" and read-only
        self.from_party_input = QLineEdit()
        self.from_party_input.setText("UNIVERSAL DYEING")
        self.from_party_input.setReadOnly(True)
        self.from_party_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #888888;
            }
        """)
        form_layout.addRow("From Party:", self.from_party_input)
        
        # Outward To: Use QComboBox with Liabilities master list
        self.outward_to_input = QComboBox()
        self.outward_to_input.setEditable(True)
        self.outward_to_input.setStyleSheet(self.get_combo_style())
        self.outward_to_input.addItem("")  # Allow blank
        self.outward_to_input.lineEdit().textChanged.connect(self.auto_uppercase_text)
        form_layout.addRow("Outward To:", self.outward_to_input)
        
        self.vehicle_input = QLineEdit()
        self.vehicle_input.setStyleSheet(self.get_input_style())
        self.vehicle_input.textChanged.connect(self.auto_uppercase_text)
        form_layout.addRow("Vehicle Number:", self.vehicle_input)
        
        self.driver_input = QLineEdit()
        self.driver_input.setStyleSheet(self.get_input_style())
        self.driver_input.textChanged.connect(self.auto_uppercase_text)
        form_layout.addRow("Driver Name:", self.driver_input)
        
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setStyleSheet(self.get_input_style())
        form_layout.addRow("Date:", self.date_input)
        
        layout.addLayout(form_layout)
        
        items_label = QLabel("Items (Select MS Party first to load available stock):")
        items_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(items_label)
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(4)
        self.items_table.setHorizontalHeaderLabels(["Item Name", "Measurement", "Available Stock", "Outward Quantity"])
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        # Connect itemChanged to auto-uppercase item names
        self.items_table.itemChanged.connect(self.on_item_changed)
        self.items_table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                gridline-color: #3d3d3d;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                padding: 8px;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.items_table)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_outward)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
        # Don't populate form here - wait for parties to load first
        # populate_form will be called from load_parties_with_stock when parties are ready
    
    def setup_autocomplete(self):
        """Set up autocomplete for Outward To field using Liabilities master list"""
        try:
            # Get Liabilities master list (same as MS Party)
            response = self.api_client._try_request("GET", "/api/parties")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.liabilities_list = data.get("parties", [])
                    liability_names = [p['name'] for p in self.liabilities_list]
                    
                    # Populate Outward To combo with liabilities (clear first to avoid duplicates)
                    if hasattr(self, 'outward_to_input') and self.outward_to_input:
                        # Clear existing items (except blank item if present)
                        current_text = self.outward_to_input.currentText()
                        self.outward_to_input.clear()
                        self.outward_to_input.addItem("")  # Allow blank
                        # Add unique liability names only
                        seen = set()
                        for name in liability_names:
                            if name and name not in seen:
                                self.outward_to_input.addItem(name)
                                seen.add(name)
                        # Restore current text if it was set
                        if current_text:
                            index = self.outward_to_input.findText(current_text)
                            if index >= 0:
                                self.outward_to_input.setCurrentIndex(index)
                            else:
                                self.outward_to_input.setCurrentText(current_text)
                        
                        # Set up completer for suggestions
                        from PyQt5.QtWidgets import QCompleter
                        from PyQt5.QtCore import Qt
                        outward_completer = QCompleter(liability_names, self.outward_to_input)
                        outward_completer.setCaseSensitivity(Qt.CaseInsensitive)
                        outward_completer.setCompletionMode(QCompleter.PopupCompletion)
                        outward_completer.setFilterMode(Qt.MatchContains)
                        outward_completer.setMaxVisibleItems(10)
                        self.outward_to_input.setCompleter(outward_completer)
                        
                        # Style the completer popup
                        outward_completer.popup().setStyleSheet("""
                            QListView {
                                background-color: #1e1e1e;
                                border: 1px solid #3d3d3d;
                                color: #ffffff;
                                selection-background-color: #0078d4;
                                selection-color: #ffffff;
                                padding: 2px;
                            }
                        """)
        except Exception as e:
            print(f"Error setting up autocomplete: {e}")
            import traceback
            traceback.print_exc()
    
    def save_party_name_if_new(self, party_name):
        """Save party name to global parties table if it's new"""
        if not party_name or not party_name.strip():
            return
        
        party_name = party_name.strip()
        try:
            # Try to save the party name (API will handle if it already exists)
            response = requests.post(
                "/api/save-party-name",
                json={"party_name": party_name}
            )
            # Don't show error to user - just silently save if new
        except:
            pass  # Silently fail - user can still use the name
    
    def populate_form(self):
        """Populate form when editing existing document"""
        if not self.document:
            return
        
        # Ensure combo box has been populated (safety check)
        if self.ms_party_combo.count() <= 1:  # Only has "-- Select MS Party --"
            print(f"[OutwardDialog] WARNING: Combo box not populated yet, retrying in 200ms")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(200, self.populate_form)
            return
        
        print(f"[OutwardDialog] populate_form called, document: {self.document.get('id') if self.document else None}")
        print(f"[OutwardDialog] MS Party ID from document: {self.document.get('ms_party_id')}")
        print(f"[OutwardDialog] Combo box count: {self.ms_party_combo.count()}")
        
        # Fill in other fields first
        # From Party: Always set to "Universal Dyeing" (read-only)
        self.from_party_input.setText("UNIVERSAL DYEING")
        
        # Outward To: Set liability name from document
        outward_to_name = self.document.get('outward_to', '')
        if outward_to_name:
            if hasattr(self, 'outward_to_input') and self.outward_to_input:
                index = self.outward_to_input.findText(outward_to_name)
                if index >= 0:
                    self.outward_to_input.setCurrentIndex(index)
                else:
                    # If not found (legacy data), add temporarily
                    self.outward_to_input.addItem(outward_to_name)
                    self.outward_to_input.setCurrentText(outward_to_name)
        self.vehicle_input.setText(self.document.get('vehicle_number', ''))
        self.driver_input.setText(self.document.get('driver_name', ''))
        
        date_str = self.document.get('document_date', '')
        if date_str:
            try:
                date = QDate.fromString(date_str[:10], "yyyy-MM-dd")
                self.date_input.setDate(date)
            except:
                pass
        
        # Set MS Party last (this will trigger on_party_selected and populate stock)
        # Temporarily disconnect to avoid triggering during setup
        try:
            self.ms_party_combo.currentIndexChanged.disconnect()
        except TypeError:
            pass  # Not connected yet
        
        ms_party_id = self.document.get('ms_party_id')
        # Convert to int if it's not None (handle both int and string types)
        if ms_party_id is not None:
            try:
                ms_party_id = int(ms_party_id)
            except (ValueError, TypeError):
                print(f"[OutwardDialog] ERROR: Could not convert ms_party_id to int: {ms_party_id}")
                ms_party_id = None
        
        party_found = False
        if ms_party_id is not None:
            for i in range(self.ms_party_combo.count()):
                combo_data = self.ms_party_combo.itemData(i)
                # Convert combo data to int for comparison
                try:
                    combo_data_int = int(combo_data) if combo_data is not None else None
                    if combo_data_int == ms_party_id:
                        print(f"[OutwardDialog] Found MS Party at index {i}, setting current index")
                        self.ms_party_combo.setCurrentIndex(i)
                        party_found = True
                        break
                except (ValueError, TypeError):
                    continue
        
        # Reconnect signal
        self.ms_party_combo.currentIndexChanged.connect(self.on_party_selected)
        
        # If party was found, manually trigger stock loading
        if party_found:
            print(f"[OutwardDialog] Party found, triggering on_party_selected")
            self.on_party_selected()
        else:
            print(f"[OutwardDialog] WARNING: Party not found in combo box. MS Party ID: {ms_party_id}")
            # Party not found - try to set it anyway (might have been added by load_parties_with_stock)
            # Try one more time to find it
            if ms_party_id is not None:
                for i in range(self.ms_party_combo.count()):
                    combo_data = self.ms_party_combo.itemData(i)
                    try:
                        combo_data_int = int(combo_data) if combo_data is not None else None
                        if combo_data_int == ms_party_id:
                            print(f"[OutwardDialog] Found MS Party on retry at index {i}")
                            self.ms_party_combo.setCurrentIndex(i)
                            self.on_party_selected()
                            return
                    except (ValueError, TypeError):
                        continue
            print(f"[OutwardDialog] ERROR: Could not find MS Party {ms_party_id} in combo box")
    
    def update_quantities_from_document(self):
        """Update quantities in table from document items (called after stock loads)"""
        if not self.document:
            return
        
        items = self.document.get('items', [])
        # Create a dict for quick lookup and store original quantities
        doc_items = {}
        self.original_document_quantities = {}
        for item in items:
            key = (item.get('item_name', ''), item.get('measurement', 15))
            qty = item.get('quantity', 0)
            doc_items[key] = qty
            self.original_document_quantities[key] = qty
        
        # Update quantities in table
        for row in range(self.items_table.rowCount()):
            name_item = self.items_table.item(row, 0)
            measurement_item = self.items_table.item(row, 1)
            qty_item = self.items_table.item(row, 3)
            
            if name_item and measurement_item and qty_item:
                item_name = name_item.text()
                measurement = int(measurement_item.text())
                key = (item_name, measurement)
                
                if key in doc_items:
                    qty_item.setText(str(doc_items[key]))
    
    def save_outward(self):
        ms_party_id = self.ms_party_combo.currentData()
        if not ms_party_id:
            QMessageBox.warning(self, "Validation", "Please select MS Party")
            return
        
        items = []
        for row in range(self.items_table.rowCount()):
            item_name = self.items_table.item(row, 0)
            measurement_item = self.items_table.item(row, 1)
            available_stock_item = self.items_table.item(row, 2)
            quantity_item = self.items_table.item(row, 3)
            
            if not item_name or not item_name.text().strip():
                continue
            
            item_name_str = item_name.text().strip()
            measurement = int(measurement_item.text())
            available = float(available_stock_item.text() if available_stock_item else 0)
            quantity = float(quantity_item.text() if quantity_item else 0)
            
            # Only include items with quantity > 0
            if quantity <= 0:
                continue
            
            # When editing, calculate temp_check = available_stock + original_outward_quantity
            # This allows editing up to the original quantity + what's currently available
            # Example: available=400, original_outward=200, temp_check=600, user can edit up to 600
            key = (item_name_str, measurement)
            if self.document and key in self.original_document_quantities:
                original_qty = self.original_document_quantities[key]
                temp_check = original_qty + available
                if quantity > temp_check:
                    QMessageBox.warning(self, "Validation", 
                        f"Quantity exceeds available stock for {item_name_str} ({measurement}).\n"
                        f"Available stock: {available}, Original outward quantity: {original_qty}\n"
                        f"Maximum allowed: {temp_check}, Requested: {quantity}")
                    return
            else:
                # New item (not in original document) - just check against available stock
                if quantity > available:
                    QMessageBox.warning(self, "Validation", 
                        f"Insufficient stock for {item_name_str} ({measurement}). Available: {available}, Requested: {quantity}")
                    return
            
            items.append({
                "item_name": item_name_str,
                "measurement": measurement,
                "quantity": quantity
            })
        
        if not items:
            QMessageBox.warning(self, "Validation", "Please enter outward quantity for at least one item")
            return
        
        # From Party: Always "Universal Dyeing"
        from_party_name = "UNIVERSAL DYEING"
        
        # Outward To: Validate against Liabilities master list
        outward_to_name = ""
        if hasattr(self, 'outward_to_input') and self.outward_to_input:
            outward_to_name = self.outward_to_input.currentText().strip()
            if outward_to_name:
                valid_names = [p.get("name", "") for p in (getattr(self, 'liabilities_list', []) or [])]
                if outward_to_name not in valid_names:
                    QMessageBox.warning(
                        self,
                        "Validation",
                        "Outward To must be selected from Liabilities master list.",
                    )
                    return
        
        data = {
            "ms_party_id": ms_party_id,
            "from_party": from_party_name,
            "outward_to": outward_to_name,
            "vehicle_number": self.vehicle_input.text(),
            "driver_name": self.driver_input.text(),
            "document_date": self.date_input.date().toString("yyyy-MM-dd"),
            "items": items,
            "created_by": self.user_data.get('username', 'Unknown') if self.user_data else 'Unknown'
        }
        
        try:
            if self.document:
                data["outward_id"] = self.document['id']
                response = self.api_client._try_request_with_retry("PUT", "/api/outward", json=data)
            else:
                response = self.api_client._try_request_with_retry("POST", "/api/outward", json=data)
            
            if response and response.status_code in [200, 201]:
                result = response.json()
                if result.get("success"):
                    QMessageBox.information(self, "Success", "Document saved successfully")
                    if isinstance(result.get("document"), dict):
                        self.saved_document = result.get("document")
                    self.accept()
                else:
                    QMessageBox.warning(self, "Error", result.get("message", "Failed to save"))
            elif response is None:
                # Connection failed after all retries
                QMessageBox.warning(
                    self, "Connection Error",
                    "Unable to connect to the server after multiple attempts.\n\n"
                    "Please check your network connection and try again.\n"
                    "Your data has been preserved in the form."
                )
            else:
                error_msg = "Unknown error"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", error_msg)
                except:
                    pass
                QMessageBox.warning(self, "Error", f"Server error: {error_msg}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")


# ==================== STOCK MODULE (READ-ONLY) ====================

class StockModule(QWidget):
    """Stock Module - Read-only reports"""
    
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data
        self.server_available = True
        self.api_client = APIClient()
        self.init_ui()
        self.load_parties()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("📦 Stock Reports (Read-Only)")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)
        header.addStretch()
        
        # Party selection
        party_label = QLabel("Select MS Party:")
        party_label.setStyleSheet("color: #ffffff;")
        header.addWidget(party_label)
        
        self.party_combo = QComboBox()
        self.party_combo.setMinimumWidth(200)
        self.party_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
            }
            QComboBox:focus {
                border: 2px solid #0078d4;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #ffffff;
                selection-background-color: #0078d4;
            }
        """)
        self.party_combo.currentIndexChanged.connect(self.on_party_selected)
        header.addWidget(self.party_combo)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        self.refresh_btn.clicked.connect(self.load_stock)
        header.addWidget(self.refresh_btn)
        
        self.print_btn = QPushButton("🖨️ Print")
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                border: 1px solid #005a9e;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.print_btn.clicked.connect(self.print_stock_report)
        header.addWidget(self.print_btn)
        
        layout.addLayout(header)
        
        # Info label
        info_label = QLabel("Stock is calculated automatically from Inward, Transfer (Simple), Transfer BN, and Outward documents.")
        info_label.setStyleSheet("color: #888888; font-style: italic; padding: 10px;")
        layout.addWidget(info_label)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Item Name", "Measurement", "Inward",
            "Transfer\n(Simple)", "Transfer\nBN IN", "Transfer\nBN OUT",
            "Total\nOutward", "Remaining"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #252525;
                border: 1px solid #3d3d3d;
                gridline-color: #3d3d3d;
                color: #ffffff;
            }
            QTableWidget::item {
                padding: 5px;
                background-color: #1e1e1e;
            }
            QTableWidget::item:alternate {
                background-color: #252525;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QTableWidget::item:selected:alternate {
                background-color: #0078d4;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                padding: 10px 8px;
                border: none;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        self.table.setAlternatingRowColors(True)
        # Set column widths for better spacing
        self.table.setColumnWidth(0, 150)  # Item Name
        self.table.setColumnWidth(1, 120)  # Measurement
        self.table.setColumnWidth(2, 100)  # Inward
        self.table.setColumnWidth(3, 140)  # Transfer (Simple)
        self.table.setColumnWidth(4, 140)  # Transfer BN IN (increased width)
        self.table.setColumnWidth(5, 150)  # Transfer BN OUT (increased width)
        self.table.setColumnWidth(6, 130)  # Total Outward
        # Remaining will stretch
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def load_parties(self):
        """Load parties from API"""
        try:
            response = self.api_client._try_request("GET", "/api/parties")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    parties = data.get("parties", [])
                    self.party_combo.clear()
                    self.party_combo.addItem("-- Select Party --", None)
                    for party in parties:
                        self.party_combo.addItem(party['name'], party['id'])
        except:
            self.server_available = False
    
    def on_party_selected(self):
        """Load stock when party is selected"""
        party_id = self.party_combo.currentData()
        if party_id:
            self.load_stock()
    
    def load_stock(self):
        """Load stock for selected party"""
        party_id = self.party_combo.currentData()
        if not party_id:
            self.table.setRowCount(0)
            return
        
        try:
            response = self.api_client._try_request("GET", f"/api/stock/{party_id}")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    stock = data.get("stock", [])
                    self.populate_table(stock)
                else:
                    QMessageBox.warning(self, "Error", data.get("message", "Failed to load stock"))
            else:
                QMessageBox.warning(self, "Error", f"Server returned status {response.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load stock: {str(e)}")
    
    def populate_table(self, stock):
        """Populate table with stock data"""
        self.table.setRowCount(len(stock))
        for row, item in enumerate(stock):
            self.table.setItem(row, 0, QTableWidgetItem(item.get('item_name', '')))
            self.table.setItem(row, 1, QTableWidgetItem(str(item.get('measurement', ''))))
            self.table.setItem(row, 2, QTableWidgetItem(str(item.get('total_inward', 0))))
            self.table.setItem(row, 3, QTableWidgetItem(str(item.get('total_transfer', 0))))  # Transfer (Simple)
            self.table.setItem(row, 4, QTableWidgetItem(str(item.get('transfer_bn_in', 0))))  # Transfer BN IN
            self.table.setItem(row, 5, QTableWidgetItem(str(item.get('transfer_bn_out', 0))))  # Transfer BN OUT
            self.table.setItem(row, 6, QTableWidgetItem(str(item.get('total_outward', 0))))
            
            # Remaining stock - highlight if low
            remaining = item.get('remaining_stock', 0)
            remaining_item = QTableWidgetItem(str(remaining))
            if remaining < 0:
                remaining_item.setForeground(Qt.red)
            elif remaining == 0:
                remaining_item.setForeground(Qt.yellow)
            self.table.setItem(row, 7, remaining_item)
        
        # Store stock data for printing
        self.current_stock_data = stock
        self.current_party_name = self.party_combo.currentText()
    
    def print_stock_report(self):
        """Print the current stock report"""
        if not hasattr(self, 'current_stock_data') or not self.current_stock_data:
            QMessageBox.warning(self, "No Data", "No stock data to print. Please select a party and load stock first.")
            return
        
        try:
            html_content = self.generate_stock_print_html(self.current_stock_data, self.current_party_name)
            
            # Create temporary HTML file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
            # Open in default browser for printing
            QDesktopServices.openUrl(QUrl.fromLocalFile(temp_file.name))
            
            QMessageBox.information(
                self, "Print", 
                "Print dialog opened. Please use Ctrl+P or File > Print to print the document."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate print document: {str(e)}")
    
    def find_logo_file(self):
        """Find logo file in common locations"""
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "logo.png"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png"),
            "assets/logo.png",
            "logo.png"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def generate_stock_print_html(self, stock_data, party_name):
        """Generate print-ready HTML for stock report"""
        logo_path = self.find_logo_file()
        logo_html = ''
        if logo_path:
            try:
                with open(logo_path, 'rb') as logo_file:
                    logo_data = logo_file.read()
                    logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                    logo_ext = os.path.splitext(logo_path)[1].lower()
                    mime_type = 'image/png' if logo_ext == '.png' else 'image/jpeg' if logo_ext in ['.jpg', '.jpeg'] else 'image/svg+xml' if logo_ext == '.svg' else 'image/png'
                    logo_html = f'<img src="data:{mime_type};base64,{logo_base64}" alt="Logo" style="max-width: 200px; max-height: 200px;" />'
            except:
                logo_html = '<div style="width: 200px; height: 200px; border: 1px dashed #ccc;">LOGO</div>'
        else:
            logo_html = '<div style="width: 200px; height: 200px; border: 1px dashed #ccc; display: flex; align-items: center; justify-content: center; font-size: 10px;">LOGO</div>'
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Stock Report</title>
    <style>
        @media print {{
            @page {{
                size: A4 landscape;
                margin: 10mm;
            }}
            body {{
                margin: 0;
                padding: 0;
            }}
        }}
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            color: #000;
        }}
        .header {{
            text-align: center;
            margin-bottom: 20px;
            border-bottom: 2px solid #000;
            padding-bottom: 10px;
        }}
        .logo {{
            display: inline-block;
            vertical-align: middle;
            margin-right: 20px;
        }}
        .company-info {{
            display: inline-block;
            vertical-align: middle;
            text-align: left;
        }}
        .company-name {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .owner-info {{
            font-size: 12px;
            margin-top: 5px;
        }}
        .report-title {{
            font-size: 20px;
            font-weight: bold;
            text-align: center;
            margin: 15px 0;
        }}
        .report-info {{
            margin-bottom: 15px;
            font-size: 12px;
        }}
        .report-info table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .report-info td {{
            padding: 3px 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 10px;
        }}
        th, td {{
            border: 1px solid #000;
            padding: 5px;
            text-align: left;
        }}
        th {{
            background-color: #f0f0f0;
            font-weight: bold;
            text-align: center;
        }}
        .text-right {{
            text-align: right;
        }}
        .text-center {{
            text-align: center;
        }}
        .footer {{
            margin-top: 20px;
            font-size: 10px;
            text-align: center;
            border-top: 1px solid #000;
            padding-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">{logo_html}</div>
        <div class="company-info">
            <div class="company-name">MOMINA LACE DYEING</div>
            <div class="owner-info">
                Owner : GHULAM MUSTAFA<br>
                GM : Shahid, Naveed
            </div>
        </div>
    </div>
    
    <div class="report-title">STOCK REPORT</div>
    
    <div class="report-info">
        <table>
            <tr>
                <td><strong>Party:</strong> {party_name}</td>
                <td><strong>Generated:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</td>
            </tr>
            <tr>
                <td><strong>Total Items:</strong> {len(stock_data)}</td>
                <td></td>
            </tr>
        </table>
    </div>
    
    <table>
        <thead>
            <tr>
                <th style="width: 20%;">Item Name</th>
                <th style="width: 10%;">Measurement</th>
                <th style="width: 10%;" class="text-right">Inward</th>
                <th style="width: 12%;" class="text-right">Transfer (Simple)</th>
                <th style="width: 12%;" class="text-right">Transfer BN IN</th>
                <th style="width: 12%;" class="text-right">Transfer BN OUT</th>
                <th style="width: 12%;" class="text-right">Total Outward</th>
                <th style="width: 12%;" class="text-right">Remaining</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for item in stock_data:
            remaining = item.get('remaining_stock', 0)
            remaining_class = ' style="color: red;"' if remaining < 0 else ' style="color: orange;"' if remaining == 0 else ''
            
            html += f"""
            <tr>
                <td>{item.get('item_name', '')}</td>
                <td class="text-center">{item.get('measurement', '')}</td>
                <td class="text-right">{item.get('total_inward', 0)}</td>
                <td class="text-right">{item.get('total_transfer', 0)}</td>
                <td class="text-right">{item.get('transfer_bn_in', 0)}</td>
                <td class="text-right">{item.get('transfer_bn_out', 0)}</td>
                <td class="text-right">{item.get('total_outward', 0)}</td>
                <td class="text-right"{remaining_class}>{remaining}</td>
            </tr>
"""
        
        html += """
        </tbody>
    </table>
    
    <div class="footer">
        <div>SITE: Small Industrial State, Sargodha Road, Faisalabad</div>
        <div>CONTACTS: 0321-7651815, 0300-8651815, 0304-6166663, 0300-8636129</div>
    </div>
    
    <script>
        window.onload = function() {
            window.print();
        };
    </script>
</body>
</html>
"""
        return html

