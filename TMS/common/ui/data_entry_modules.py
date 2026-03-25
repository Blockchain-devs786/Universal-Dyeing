"""Data Entry Modules: Inward, Transfer, Outward, Stock"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QLineEdit, QFormLayout,
    QDialogButtonBox, QMessageBox, QComboBox, QDoubleSpinBox, QDateEdit,
    QAbstractItemView, QSpinBox, QListWidget, QListWidgetItem, QCheckBox
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QFont, QDesktopServices
from datetime import datetime
import requests
import os
import tempfile
import webbrowser
from common.config import CLIENT_FALLBACK_SERVER
from client.api_client import APIClient

# Import DocumentLoader from the other file to avoid circular import
# We'll define it locally if needed, or import it after the other file is loaded


# ==================== INWARD MODULE ====================

class InwardModule(QWidget):
    """Inward Data Entry Module"""
    
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data
        self.ws_bus = (user_data or {}).get("ws_bus")
        self.server_available = True
        self.api_client = APIClient()
        # Set username on API client for edited_by tracking
        if user_data and user_data.get('username'):
            self.api_client.set_username(user_data.get('username'))
        self._data_loaded = False  # Track if data has been loaded
        self.init_ui()
        if self.ws_bus:
            try:
                self.ws_bus.message.connect(self.on_realtime_message)
            except Exception:
                pass
        # Don't load data immediately - wait until module is shown

    def load_data_if_needed(self):
        """Load data if not already loaded (called explicitly when module is shown)"""
        if not self._data_loaded:
            self._data_loaded = True
            self.load_documents_async()
    
    def showEvent(self, event):
        """Handle show event (but don't load here - use load_data_if_needed instead)"""
        super().showEvent(event)

    def on_realtime_message(self, message: dict):
        """Apply server-pushed CRUD updates (so client UIs update instantly)."""
        if not isinstance(message, dict):
            return
        if message.get("type") != "entity_change":
            return
        if message.get("entity") != "inward":
            return

        action = message.get("action")
        data = message.get("data") or {}
        if action in ("created", "updated"):
            if isinstance(data, dict) and data.get("id"):
                self._upsert_document(data, prefer_top=(action == "created"))
        elif action == "deleted":
            doc_id = None
            if isinstance(data, dict):
                doc_id = data.get("id")
            if doc_id:
                self._remove_document_by_id(doc_id)

    def _upsert_document(self, doc: dict, prefer_top: bool = False):
        """Insert or update a document in the in-memory list and refresh table view."""
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
        title = QLabel("📥 Inward Documents")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)
        header.addStretch()
        
        # Buttons
        self.add_btn = QPushButton("➕ Add Inward")
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
        self.add_btn.clicked.connect(self.add_inward)
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
        self.ms_party_filter.textChanged.connect(self.auto_uppercase_text)
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
        
        # INWARD # Filter
        inward_label = QLabel("INWARD #:")
        inward_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        filter_layout.addWidget(inward_label)
        
        self.inward_filter = QLineEdit()
        self.inward_filter.setPlaceholderText("Filter by INWARD #...")
        self.inward_filter.setStyleSheet("""
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
        self.inward_filter.textChanged.connect(self.filter_table)
        self.inward_filter.textChanged.connect(self.auto_uppercase_text)
        filter_layout.addWidget(self.inward_filter)
        
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
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "INWARD #", "GP #", "SR #", "MS Party", "From Party",
            "Vehicle #", "Driver", "Total Qty", "Date"
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
        self.table.doubleClicked.connect(self.edit_selected_inward)
        layout.addWidget(self.table)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.clicked.connect(self.edit_selected_inward)
        self.edit_btn.setEnabled(False)
        action_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self.delete_selected_inward)
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
        self.print_btn.clicked.connect(self.print_inwards)
        action_layout.addWidget(self.print_btn)
        
        layout.addLayout(action_layout)
        
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        self.setLayout(layout)
    
    def on_selection_changed(self):
        """Enable/disable edit/delete buttons based on selection"""
        has_selection = len(self.table.selectedItems()) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def auto_uppercase_text(self, text):
        """Automatically convert text to uppercase as user types (including MS Party filter)."""
        sender = self.sender()
        if sender:
            cursor_pos = sender.cursorPosition()
            uppercase_text = text.upper()
            if text != uppercase_text:
                sender.blockSignals(True)
                sender.setText(uppercase_text)
                sender.setCursorPosition(min(cursor_pos, len(uppercase_text)))
                sender.blockSignals(False)
    
    def load_documents_async(self):
        """Load documents asynchronously"""
        self.loader = DocumentLoader("inward")
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
                    # Filter to active parties only for autocomplete
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
        inward_filter = ""
        from_date = QDate(2000, 1, 1)
        to_date = QDate(2099, 12, 31)
        
        try:
            if hasattr(self, 'ms_party_filter') and self.ms_party_filter is not None:
                ms_party_filter = self.ms_party_filter.text().upper()
            if hasattr(self, 'gp_filter') and self.gp_filter is not None:
                gp_filter = self.gp_filter.text().upper()
            if hasattr(self, 'inward_filter') and self.inward_filter is not None:
                inward_filter = self.inward_filter.text().upper()
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
            
            # Check INWARD # filter
            matches_inward = True
            if inward_filter:
                inward_num = doc.get('inward_number', '').upper()
                matches_inward = inward_filter in inward_num
            
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
            if matches_ms_party and matches_gp and matches_inward and matches_date:
                filtered_docs.append(doc)
        
        # Populate table with filtered documents
        try:
            self.table.setRowCount(len(filtered_docs))
            for row, doc in enumerate(filtered_docs):
                self.table.setItem(row, 0, QTableWidgetItem(doc.get('inward_number', '')))
                self.table.setItem(row, 1, QTableWidgetItem(doc.get('gp_number', '')))
                self.table.setItem(row, 2, QTableWidgetItem(doc.get('sr_number', '')))
                self.table.setItem(row, 3, QTableWidgetItem(doc.get('ms_party_name', '')))
                self.table.setItem(row, 4, QTableWidgetItem(doc.get('from_party', '')))
                self.table.setItem(row, 5, QTableWidgetItem(doc.get('vehicle_number', '')))
                self.table.setItem(row, 6, QTableWidgetItem(doc.get('driver_name', '')))
                self.table.setItem(row, 7, QTableWidgetItem(str(doc.get('total_quantity', 0))))
                date_str = doc.get('document_date', '')
                if date_str:
                    date_str = date_str[:10]  # Just the date part
                self.table.setItem(row, 8, QTableWidgetItem(date_str))
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
        if hasattr(self, 'inward_filter'):
            self.inward_filter.clear()
        if hasattr(self, 'from_date_input'):
            self.from_date_input.setDate(QDate(2000, 1, 1))
        if hasattr(self, 'to_date_input'):
            self.to_date_input.setDate(QDate(2099, 12, 31))
        if hasattr(self, 'all_documents'):
            self.filter_table()
    
    def on_load_error(self, error):
        """Handle load error"""
        QMessageBox.warning(self, "Error", f"Failed to load documents: {error}")
        self.server_available = False
    
    def add_inward(self):
        """Show add inward dialog"""
        if not self.server_available:
            QMessageBox.warning(self, "Server Offline", "Server is not available.")
            return
        
        dialog = InwardDialog(self, user_data=self.user_data)
        if dialog.exec_() == QDialog.Accepted:
            saved = getattr(dialog, "saved_document", None)
            if isinstance(saved, dict) and saved.get("id"):
                self._upsert_document(saved, prefer_top=True)
            else:
                # Fallback (older server) - refresh
                self.load_documents_async()
    
    def edit_selected_inward(self):
        """Edit selected inward document"""
        selected = self.table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        doc_id = self.table.item(row, 0).data(Qt.UserRole)
        
        # Load document details
        try:
            response = self.api_client._try_request("GET", f"/api/inward/{doc_id}")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    document = data.get("document")
                    dialog = InwardDialog(self, document=document, user_data=self.user_data)
                    if dialog.exec_() == QDialog.Accepted:
                        saved = getattr(dialog, "saved_document", None)
                        if isinstance(saved, dict) and saved.get("id"):
                            self._upsert_document(saved, prefer_top=False)
                        else:
                            self.load_documents_async()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load document: {str(e)}")
    
    def delete_selected_inward(self):
        """Delete selected inward document"""
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
                response = self.api_client._try_request_with_retry("DELETE", f"/api/inward/{doc_id}")
                if response:
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            QMessageBox.information(self, "Success", "Document deleted successfully")
                            self._remove_document_by_id(doc_id)
                        else:
                            QMessageBox.warning(self, "Error", data.get("message", "Failed to delete"))
                    else:
                        QMessageBox.warning(self, "Error", f"Server returned status {response.status_code}")
                else:
                    QMessageBox.warning(self, "Error", "Connection error: Unable to reach server")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")
    
    def print_inwards(self):
        """Show print dialog and print selected inwards"""
        # Get selected rows
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one inward document to print")
            return
        
        # Show print dialog
        dialog = PrintInwardDialog(self, selected_rows, self.all_documents)
        if dialog.exec_() == QDialog.Accepted:
            selected_ids = dialog.get_selected_ids()
            if selected_ids:
                self.generate_and_print_html(selected_ids)
    
    def find_logo_file(self):
        """Find logo file in common locations"""
        # Possible logo file names
        logo_names = ['logo.png', 'logo.jpg', 'logo.jpeg', 'logo.svg', 'company_logo.png', 'company_logo.jpg']
        
        # Search in common locations
        search_paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'assets'),  # common/ui/../../assets
            os.path.join(os.path.dirname(__file__), '..', 'assets'),  # common/ui/../assets
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
    
    def generate_and_print_html(self, inward_ids):
        """Generate HTML for printing and open in Chrome"""
        try:
            # Fetch all inward documents
            inwards = []
            for inward_id in inward_ids:
                response = self.api_client._try_request("GET", f"/api/inward/{inward_id}")
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        inwards.append(data.get("document"))
            
            if not inwards:
                QMessageBox.warning(self, "Error", "No inward documents found to print")
                return
            
            # Generate HTML
            html_content = self.generate_print_html(inwards)
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
            # Open in Chrome
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
                # Fallback to default browser
                webbrowser.open('file://' + temp_file.name)
                QMessageBox.information(
                    self, "Print", 
                    "Print dialog opened. Please use Ctrl+P or File > Print to print the document."
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate print document: {str(e)}")
    
    def generate_print_html(self, inwards):
        """Generate print-ready HTML for inward documents"""
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Print Inward Documents</title>
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
        
        # Group inwards into pages (2 per page)
        pages = []
        for i in range(0, len(inwards), 2):
            page_inwards = inwards[i:i+2]
            pages.append(page_inwards)
        
        # Generate HTML for each page
        for page_idx, page_inwards in enumerate(pages):
            html += '<div class="page">\n'
            
            for form_idx, inward in enumerate(page_inwards):
                html += self.generate_inward_form_html(inward)
                
                # Add cut line between forms on same page (not after last form)
                if form_idx < len(page_inwards) - 1:
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
    
    def generate_inward_form_html(self, inward):
        """Generate HTML for a single inward form"""
        # Get items
        items = inward.get('items', [])
        
        # Format date
        doc_date = inward.get('document_date', '')
        if doc_date:
            try:
                date_obj = datetime.strptime(doc_date[:10], '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d-%m-%Y')
            except:
                formatted_date = doc_date[:10]
        else:
            formatted_date = ''
        
        # Find logo file
        logo_path = self.find_logo_file()
        logo_html = ''
        if logo_path:
            # Convert logo to base64 for embedding
            try:
                import base64
                with open(logo_path, 'rb') as logo_file:
                    logo_data = logo_file.read()
                    logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                    logo_ext = os.path.splitext(logo_path)[1].lower()
                    mime_type = 'image/png' if logo_ext == '.png' else 'image/jpeg' if logo_ext in ['.jpg', '.jpeg'] else 'image/svg+xml' if logo_ext == '.svg' else 'image/png'
                    logo_html = f'<img src="data:{mime_type};base64,{logo_base64}" alt="Logo" style="background: transparent; width: 100%; height: 100%; object-fit: contain;" />'
            except Exception as e:
                # Fallback to file path if base64 fails
                logo_html = f'<img src="{logo_path}" alt="Logo" style="background: transparent; width: 100%; height: 100%; object-fit: contain;" />'
        else:
            # Placeholder if logo not found
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
        
        <div class="subtitle">GOODS IN</div>
        
        <div class="meta-info">
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">SR# :</span>
                    <span class="meta-value">{inward.get('sr_number', '')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">DATE :</span>
                    <span class="meta-value">{formatted_date}</span>
                </div>
            </div>
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">MS PARTY :</span>
                    <span class="meta-value">{inward.get('ms_party_name', '')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">FROM :</span>
                    <span class="meta-value">{inward.get('from_party', '')}</span>
                </div>
            </div>
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-label">VEHICLE NO :</span>
                    <span class="meta-value">{inward.get('vehicle_number', '')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">DRIVER :</span>
                    <span class="meta-value">{inward.get('driver_name', '')}</span>
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
        
        # Add items
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
        
        # Add empty rows if needed (minimum 3 rows)
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
                <span class="footer-value">{inward.get('created_by', '')}</span>
            </div>
            <div class="footer-row">
                <span class="footer-label">EDITED BY :</span>
                <span class="footer-value">{inward.get('edited_by', 'None') if inward.get('edited_by') else 'None'}</span>
            </div>
            {('' if not inward.get('edit_log_history') else f'<div class="footer-row"><span class="footer-label">EDIT LOG HISTORY :</span><span class="footer-value" style="font-size: 10px;">{inward.get("edit_log_history", "None")}</span></div>')}
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


class PrintInwardDialog(QDialog):
    """Dialog for selecting inwards to print"""
    
    def __init__(self, parent=None, selected_rows=None, all_documents=None):
        super().__init__(parent)
        self.selected_ids = []
        self.all_documents = all_documents or []
        self.selected_rows = selected_rows or set()
        self.setWindowTitle("Print Inward Documents")
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
        
        # Instructions
        instructions = QLabel("Select inward documents to print:")
        instructions.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        layout.addWidget(instructions)
        
        # List widget with checkboxes
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
        
        # Populate list with all documents
        for idx, doc in enumerate(self.all_documents):
            item_text = f"{doc.get('inward_number', '')} - {doc.get('ms_party_name', '')} - {doc.get('document_date', '')[:10]}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, doc.get('id'))
            
            # Pre-select if row was selected in table
            if idx in self.selected_rows:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            self.list_widget.addItem(item)
        
        layout.addWidget(self.list_widget)
        
        # Buttons
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
        """Select all items"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Checked)
    
    def deselect_all(self):
        """Deselect all items"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Unchecked)
    
    def get_selected_ids(self):
        """Get IDs of selected inwards"""
        selected_ids = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                inward_id = item.data(Qt.UserRole)
                if inward_id:
                    selected_ids.append(inward_id)
        return selected_ids


class InwardDialog(QDialog):
    """Dialog for adding/editing inward document"""
    
    def __init__(self, parent=None, document=None, user_data=None):
        super().__init__(parent)
        self.document = document
        self.user_data = user_data
        self.parties = []
        self.api_client = APIClient()
        # Set username on API client for edited_by tracking
        if user_data and user_data.get('username'):
            self.api_client.set_username(user_data.get('username'))
        self.saved_document = None  # summary doc returned by server for instant UI patching
        self.setWindowTitle("Edit Inward" if document else "Add Inward")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        self.init_ui()
        # Load liabilities (MS parties) before populating form so combos have correct data
        self.load_parties()
        self.setup_autocomplete()
        # Populate after parties are loaded
        if self.document:
            self.populate_form()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Form fields
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # MS Party
        self.ms_party_combo = QComboBox()
        self.ms_party_combo.setEditable(True)
        self.ms_party_combo.setStyleSheet(self.get_combo_style())
        # Auto-uppercase MS Party text even if Caps Lock is off
        if self.ms_party_combo.lineEdit() is not None:
            self.ms_party_combo.lineEdit().textChanged.connect(self.auto_uppercase_text)
        form_layout.addRow("MS Party (Stock Owner):", self.ms_party_combo)
        
        # From Party (must be an existing liability, same master as MS Party)
        self.from_party_combo = QComboBox()
        self.from_party_combo.setEditable(True)
        self.from_party_combo.setStyleSheet(self.get_combo_style())
        # Auto-uppercase even if Caps Lock is off
        self.from_party_combo.lineEdit().textChanged.connect(self.auto_uppercase_text)
        form_layout.addRow("From Party:", self.from_party_combo)
        
        # Vehicle Number
        self.vehicle_input = QLineEdit()
        self.vehicle_input.setStyleSheet(self.get_input_style())
        self.vehicle_input.textChanged.connect(self.auto_uppercase_text)
        form_layout.addRow("Vehicle Number:", self.vehicle_input)
        
        # Driver Name
        self.driver_input = QLineEdit()
        self.driver_input.setStyleSheet(self.get_input_style())
        self.driver_input.textChanged.connect(self.auto_uppercase_text)
        form_layout.addRow("Driver Name:", self.driver_input)
        
        # Date
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setStyleSheet(self.get_input_style())
        form_layout.addRow("Date:", self.date_input)
        
        layout.addLayout(form_layout)
        
        # Items table
        items_label = QLabel("Items:")
        items_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(items_label)
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(3)
        self.items_table.setHorizontalHeaderLabels(["Item Name", "Measurement", "Quantity"])
        self.items_table.horizontalHeader().setStretchLastSection(True)
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
        
        # Item buttons
        item_btn_layout = QHBoxLayout()
        add_item_btn = QPushButton("➕ Add Item")
        add_item_btn.clicked.connect(self.add_item_row)
        item_btn_layout.addWidget(add_item_btn)
        
        remove_item_btn = QPushButton("➖ Remove Item")
        remove_item_btn.clicked.connect(self.remove_item_row)
        item_btn_layout.addWidget(remove_item_btn)
        item_btn_layout.addStretch()
        layout.addLayout(item_btn_layout)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_inward)
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
    
    def load_parties(self):
        """Load MS liabilities (parties) from API for both MS Party and From fields."""
        try:
            response = self.api_client._try_request("GET", "/api/parties")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    all_parties = data.get("parties", [])
                    # Only active parties for creating/editing documents
                    self.parties = [p for p in all_parties if p.get('is_active', True)]
                    names = [party["name"] for party in self.parties]

                    # Populate MS Party combo
                    for party in self.parties:
                        self.ms_party_combo.addItem(party["name"], party["id"])

                    # Populate From Party combo with same liability names
                    self.from_party_combo.clear()
                    self.from_party_combo.addItem("")  # Allow blank
                    for name in names:
                        self.from_party_combo.addItem(name)

                    # Attach completer to From Party combo for suggestion-style UX
                    try:
                        from PyQt5.QtWidgets import QCompleter
                        from PyQt5.QtCore import Qt
                        completer = QCompleter(names, self.from_party_combo)
                        completer.setCaseSensitivity(Qt.CaseInsensitive)
                        completer.setCompletionMode(QCompleter.PopupCompletion)
                        completer.setFilterMode(Qt.MatchContains)
                        completer.setMaxVisibleItems(10)
                        self.from_party_combo.setCompleter(completer)
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
                    except Exception:
                        pass
        except:
            pass
    
    def auto_uppercase_text(self, text):
        """Automatically convert text to uppercase as user types (all relevant fields)."""
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
        elif item.column() == 2:  # Quantity column (for Inward)
            # Validate quantity - must be positive
            try:
                quantity = float(item.text())
                if quantity < 0:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Invalid Quantity", 
                                      f"Quantity cannot be negative.\nPlease enter a positive value.")
                    # Reset to 0
                    item.setText("0")
                elif quantity == 0:
                    # Allow 0 but warn if it was previously non-zero
                    pass
            except ValueError:
                # Not a valid number - allow user to continue typing
                pass
    
    def setup_autocomplete(self):
        """(Deprecated) Autocomplete for From Party is now driven by MS liabilities list."""
        # No-op: From Party now uses the same liabilities master as MS Party via combo box.
        return
    
    def populate_form(self):
        """Populate form with document data"""
        if not self.document:
            return
        
        # ---- MS Party: try to match by ID, then by name (robust for legacy data) ----
        ms_party_id = self.document.get('ms_party_id')
        ms_party_name = (self.document.get('ms_party_name') or "").upper()

        # First, try exact ID match
        found_index = -1
        if ms_party_id is not None:
            for i in range(self.ms_party_combo.count()):
                if self.ms_party_combo.itemData(i) == ms_party_id:
                    found_index = i
                    break

        # If ID match failed, fall back to name match (case-insensitive)
        if found_index == -1 and ms_party_name:
            for i in range(self.ms_party_combo.count()):
                item_name = (self.ms_party_combo.itemText(i) or "").upper()
                if item_name == ms_party_name:
                    found_index = i
                    break

        if found_index >= 0:
            self.ms_party_combo.setCurrentIndex(found_index)
        elif ms_party_name and ms_party_id is not None:
            # Party not in combo (e.g. inactive) - add temporarily for editing
            self.ms_party_combo.addItem(self.document.get('ms_party_name', ms_party_name), ms_party_id)
            self.ms_party_combo.setCurrentIndex(self.ms_party_combo.count() - 1)
        
        # ---- From Party (liability): try to match by name (case-insensitive), else add ----
        from_name = self.document.get('from_party', '')
        if from_name:
            from_upper = from_name.upper()
            index = -1
            for i in range(self.from_party_combo.count()):
                item_name = (self.from_party_combo.itemText(i) or "").upper()
                if item_name == from_upper:
                    index = i
                    break

            if index >= 0:
                self.from_party_combo.setCurrentIndex(index)
            else:
                # If not found (e.g. legacy data), add it temporarily so user sees existing value
                self.from_party_combo.addItem(from_name)
                self.from_party_combo.setCurrentText(from_name)
        self.vehicle_input.setText(self.document.get('vehicle_number', ''))
        self.driver_input.setText(self.document.get('driver_name', ''))
        
        date_str = self.document.get('document_date', '')
        if date_str:
            try:
                date = QDate.fromString(date_str[:10], "yyyy-MM-dd")
                self.date_input.setDate(date)
            except:
                pass
        
        # Populate items
        items = self.document.get('items', [])
        self.items_table.setRowCount(len(items))
        for row, item in enumerate(items):
            self.items_table.setItem(row, 0, QTableWidgetItem(item.get('item_name', '')))
            
            # Measurement as text input (user can type 15 or 22)
            measurement_item = QTableWidgetItem(str(item.get('measurement', 15)))
            self.items_table.setItem(row, 1, measurement_item)
            
            qty_item = QTableWidgetItem(str(item.get('quantity', 0)))
            self.items_table.setItem(row, 2, qty_item)
    
    def add_item_row(self):
        """Add a new item row"""
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        
        # Item name
        self.items_table.setItem(row, 0, QTableWidgetItem(""))
        
        # Measurement as text input (user can type 15 or 22)
        measurement_item = QTableWidgetItem("")
        self.items_table.setItem(row, 1, measurement_item)
        
        # Quantity
        self.items_table.setItem(row, 2, QTableWidgetItem("0"))
    
    def remove_item_row(self):
        """Remove selected item row"""
        current_row = self.items_table.currentRow()
        if current_row >= 0:
            self.items_table.removeRow(current_row)
    
    def save_inward(self):
        """Save inward document"""
        # Get MS Party ID from combo (itemData) or validate against master list
        ms_party_name = self.ms_party_combo.currentText().strip()
        ms_party_id = self.ms_party_combo.currentData()
        if ms_party_id is None:
            valid_map = {p.get("name", ""): p.get("id") for p in (self.parties or [])}
            ms_party_id = valid_map.get(ms_party_name or "")
        if not ms_party_id:
            QMessageBox.warning(
                self,
                "Validation",
                "MS Party must be selected from Liabilities master list.",
            )
            return
        
        # Collect items
        items = []
        item_keys = set()
        for row in range(self.items_table.rowCount()):
            item_name = self.items_table.item(row, 0)
            measurement_item = self.items_table.item(row, 1)
            quantity_item = self.items_table.item(row, 2)
            
            if not item_name or not item_name.text().strip():
                continue
            
            item_name_str = item_name.text().strip()
            
            # Validate measurement
            if not measurement_item or not measurement_item.text().strip():
                QMessageBox.warning(self, "Validation", f"Please enter measurement (15 or 22) for item: {item_name_str}")
                return
            
            try:
                measurement = int(measurement_item.text().strip())
            except ValueError:
                QMessageBox.warning(self, "Validation", f"Invalid measurement for {item_name_str}. Must be 15 or 22.")
                return
            
            if measurement not in [15, 22]:
                QMessageBox.warning(self, "Validation", f"Invalid measurement for {item_name_str}. Must be 15 or 22.")
                return
            
            quantity = float(quantity_item.text() if quantity_item else 0)
            
            # Check for duplicates
            key = (item_name_str, measurement)
            if key in item_keys:
                QMessageBox.warning(self, "Validation", f"Duplicate item: {item_name_str} ({measurement})")
                return
            item_keys.add(key)
            
            items.append({
                "item_name": item_name_str,
                "measurement": measurement,
                "quantity": quantity
            })
        
        if not items:
            QMessageBox.warning(self, "Validation", "Please add at least one item")
            return
        
        # From Party must be an existing liability (name from master list)
        from_party_name = self.from_party_combo.currentText().strip()
        if from_party_name:
            valid_names = [p.get("name", "") for p in (self.parties or [])]
            if from_party_name not in valid_names:
                QMessageBox.warning(
                    self,
                    "Validation",
                    "From Party must be selected from Liabilities master list.",
                )
                return
        
        # Prepare data
        data = {
            "ms_party_id": ms_party_id,
            "from_party": from_party_name,
            "vehicle_number": self.vehicle_input.text(),
            "driver_name": self.driver_input.text(),
            "document_date": self.date_input.date().toString("yyyy-MM-dd"),
            "items": items,
            "created_by": self.user_data.get('username', 'Unknown') if self.user_data else 'Unknown'
        }
        
        try:
            if self.document:
                # Update
                data["inward_id"] = self.document['id']
                response = self.api_client._try_request_with_retry("PUT", "/api/inward", json=data)
            else:
                # Create
                response = self.api_client._try_request_with_retry("POST", "/api/inward", json=data)
            
            if response and response.status_code in [200, 201]:
                result = response.json()
                if result.get("success"):
                    QMessageBox.information(self, "Success", "Document saved successfully")
                    # Newer servers return a document summary so caller can patch UI without refetching all
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


# ==================== HELPER CLASSES ====================

class DocumentLoader(QThread):
    """Thread for loading documents"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, doc_type):
        super().__init__()
        self.doc_type = doc_type
        self.api_client = APIClient()
    
    def run(self):
        try:
            endpoint = f"/api/{self.doc_type}"
            response = self.api_client._try_request("GET", endpoint)
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

