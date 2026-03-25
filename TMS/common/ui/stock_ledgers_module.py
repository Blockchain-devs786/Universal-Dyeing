"""Stock Ledgers Module - View stock ledger entries for UD and Liability Parties"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QAbstractItemView,
    QMessageBox, QDateEdit, QGroupBox, QCheckBox, QStackedWidget, QCalendarWidget
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal, QUrl, QSize
from PyQt5.QtGui import QFont, QDesktopServices
from client.api_client import APIClient
from datetime import datetime
import os
import base64
import tempfile


class CompactDateEdit(QDateEdit):
    """DateEdit with smaller calendar popup"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        # Create a custom calendar widget with smaller size
        calendar = QCalendarWidget()
        calendar.setFixedSize(QSize(250, 200))
        calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: #2a2a2a;
                color: #ffffff;
                font-size: 9px;
                border: 1px solid #3d3d3d;
            }
            QCalendarWidget QTableView {
                selection-background-color: #0078d4;
                font-size: 9px;
                background-color: #2a2a2a;
                alternate-background-color: #252525;
                gridline-color: #3d3d3d;
            }
            QCalendarWidget QHeaderView::section {
                background-color: #1e1e1e;
                color: #ffffff;
                font-size: 9px;
                padding: 2px;
                border: none;
            }
            QCalendarWidget QToolButton {
                background-color: #1e1e1e;
                color: #ffffff;
                font-size: 9px;
                padding: 2px;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #2d2d2d;
            }
            QCalendarWidget QToolButton::menu-indicator {
                background-color: #1e1e1e;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: #2a2a2a;
                color: #ffffff;
                selection-background-color: #0078d4;
                selection-color: #ffffff;
            }
            QCalendarWidget QAbstractItemView:disabled {
                background-color: #1e1e1e;
                color: #666666;
            }
        """)
        self.setCalendarWidget(calendar)


class LedgerLoader(QThread):
    """Thread to load ledger entries asynchronously"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, api_client, ledger_id):
        super().__init__()
        self.api_client = api_client
        self.ledger_id = ledger_id
        self._is_cancelled = False
    
    def cancel(self):
        """Cancel the loading operation"""
        self._is_cancelled = True
    
    def run(self):
        try:
            if self._is_cancelled:
                return
            
            response = self.api_client._try_request("GET", f"/api/stock-ledgers/{self.ledger_id}/entries")
            
            if self._is_cancelled:
                return
            
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    if not self._is_cancelled:
                        self.finished.emit(data.get("entries", []))
                else:
                    if not self._is_cancelled:
                        self.error.emit(data.get("message", "Failed to load ledger entries"))
            else:
                if not self._is_cancelled:
                    self.error.emit(f"Server returned status {response.status_code if response else 'No response'}")
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))


class StockLedgersModule(QWidget):
    """Stock Ledgers Module - View ledger entries for UD and Liability Parties"""
    
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data
        self.server_available = True
        self.api_client = APIClient()
        self.current_ledger_id = None
        self.current_loader = None  # Track current loader thread
        self.all_entries = []  # Store all entries for filtering
        
        # State management
        self.current_view = 'filters'  # 'filters' or 'table'
        self.filtered_entries = []  # Store filtered results
        
        self.init_ui()
        self.load_ledgers()
        # Start with filters view (default)
        self.show_filters_view()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Create stacked widget for two views
        self.stacked_widget = QStackedWidget()
        
        # Create Filters View
        self.filters_view = self.create_filters_view()
        self.stacked_widget.addWidget(self.filters_view)
        
        # Create Table View
        self.table_view = self.create_table_view()
        self.stacked_widget.addWidget(self.table_view)
        
        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)
    
    def create_filters_view(self):
        """Create the filters view widget - centered report setup panel"""
        filters_widget = QWidget()
        # Outer layout for vertical centering
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(20, 20, 20, 20)
        outer_layout.setSpacing(0)
        
        # Add stretch at top for centering
        outer_layout.addStretch()
        
        # Inner card container with max-width
        card_container = QWidget()
        card_container.setMaximumWidth(900)  # Fixed max-width for premium look
        card_container.setMinimumWidth(700)  # Minimum width for proper layout
        card_container.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border: 2px solid #3d3d3d;
                border-radius: 12px;
                padding: 40px;
            }
        """)
        
        # Card layout for filters content
        filters_layout = QVBoxLayout()
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("📋 Stock Ledgers")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)
        header.addStretch()
        
        # Search/Select Ledger
        search_label = QLabel("Search Ledger:")
        search_label.setStyleSheet("color: #ffffff;")
        header.addWidget(search_label)
        
        self.ledger_combo = QComboBox()
        self.ledger_combo.setMinimumWidth(300)
        self.ledger_combo.setEditable(True)
        self.ledger_combo.setInsertPolicy(QComboBox.NoInsert)
        from PyQt5.QtWidgets import QCompleter
        completer = QCompleter()
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.ledger_combo.setCompleter(completer)
        self.ledger_combo.setStyleSheet("""
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
        self.ledger_combo.activated.connect(self.on_ledger_activated)
        self.ledger_combo.currentIndexChanged.connect(self.on_ledger_selected)
        header.addWidget(self.ledger_combo)
        
        filters_layout.addLayout(header)
        
        # Info label
        info_label = QLabel("Configure filters below and click 'Generate Report' to view the stock ledger. Ledger entries are automatically created from Inward, Outward, and Transfer transactions.")
        info_label.setStyleSheet("color: #888888; font-style: italic; padding: 10px; background-color: transparent;")
        info_label.setWordWrap(True)
        filters_layout.addWidget(info_label)
        
        # Advanced Filters Section
        filter_group = QGroupBox("🔍 Advanced Filters")
        filter_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(10)
        
        # Row 1: Date Range Filter
        date_row = QHBoxLayout()
        date_row.setSpacing(10)
        
        date_label = QLabel("Date Range:")
        date_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        date_label.setMinimumWidth(100)
        date_row.addWidget(date_label)
        
        from_date_label = QLabel("From:")
        from_date_label.setStyleSheet("color: #ffffff;")
        date_row.addWidget(from_date_label)
        
        self.from_date_edit = CompactDateEdit()
        self.from_date_edit.setDate(QDate.currentDate().addYears(-1))  # Default to 1 year ago
        self.from_date_edit.setStyleSheet("""
            QDateEdit {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 6px;
                color: #ffffff;
            }
            QDateEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        # Connect to apply filters only when in table view
        self.from_date_edit.dateChanged.connect(self.on_filter_changed)
        date_row.addWidget(self.from_date_edit)
        
        to_date_label = QLabel("To:")
        to_date_label.setStyleSheet("color: #ffffff;")
        date_row.addWidget(to_date_label)
        
        self.to_date_edit = CompactDateEdit()
        self.to_date_edit.setDate(QDate.currentDate())  # Default to today
        self.to_date_edit.setStyleSheet("""
            QDateEdit {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 6px;
                color: #ffffff;
            }
            QDateEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        self.to_date_edit.dateChanged.connect(self.on_filter_changed)
        date_row.addWidget(self.to_date_edit)
        
        date_row.addStretch()
        filter_layout.addLayout(date_row)
        
        # Row 2: Transaction Type and Particulars
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        
        trans_type_label = QLabel("Transaction Type:")
        trans_type_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        trans_type_label.setMinimumWidth(130)
        row2.addWidget(trans_type_label)
        
        self.trans_type_combo = QComboBox()
        self.trans_type_combo.setEditable(True)
        self.trans_type_combo.setInsertPolicy(QComboBox.NoInsert)
        self.trans_type_combo.setMinimumWidth(200)
        from PyQt5.QtWidgets import QCompleter
        from PyQt5.QtCore import QStringListModel
        self.trans_type_completer = QCompleter()
        self.trans_type_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.trans_type_completer.setFilterMode(Qt.MatchContains)
        self.trans_type_completer.setModel(self.trans_type_combo.model())  # Use combo box model
        self.trans_type_combo.setCompleter(self.trans_type_completer)
        self.trans_type_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 6px;
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
        self.trans_type_combo.currentTextChanged.connect(self.on_filter_changed)
        row2.addWidget(self.trans_type_combo)
        
        particulars_label = QLabel("Particulars:")
        particulars_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        particulars_label.setMinimumWidth(80)
        row2.addWidget(particulars_label)
        
        self.particulars_filter = QComboBox()
        self.particulars_filter.setEditable(True)
        self.particulars_filter.setInsertPolicy(QComboBox.NoInsert)
        self.particulars_filter.setMinimumWidth(200)
        from PyQt5.QtWidgets import QCompleter
        from PyQt5.QtCore import QStringListModel
        self.particulars_completer = QCompleter()
        self.particulars_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.particulars_completer.setFilterMode(Qt.MatchContains)
        self.particulars_completer.setModel(self.particulars_filter.model())  # Use combo box model
        self.particulars_filter.setCompleter(self.particulars_completer)
        self.particulars_filter.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 6px;
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
        self.particulars_filter.currentTextChanged.connect(self.on_filter_changed)
        row2.addWidget(self.particulars_filter)
        
        row2.addStretch()
        filter_layout.addLayout(row2)
        
        # Row 3: Item and Yard
        row3 = QHBoxLayout()
        row3.setSpacing(10)
        
        item_label = QLabel("Item:")
        item_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        item_label.setMinimumWidth(130)
        row3.addWidget(item_label)
        
        self.item_combo = QComboBox()
        self.item_combo.setEditable(True)
        self.item_combo.setInsertPolicy(QComboBox.NoInsert)
        self.item_combo.setMinimumWidth(200)
        from PyQt5.QtWidgets import QCompleter
        from PyQt5.QtCore import QStringListModel
        self.item_completer = QCompleter()
        self.item_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.item_completer.setFilterMode(Qt.MatchContains)
        self.item_completer.setModel(self.item_combo.model())  # Use combo box model
        self.item_combo.setCompleter(self.item_completer)
        self.item_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 6px;
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
        self.item_combo.currentTextChanged.connect(self.on_filter_changed)
        row3.addWidget(self.item_combo)
        
        yard_label = QLabel("Yard:")
        yard_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        yard_label.setMinimumWidth(80)
        row3.addWidget(yard_label)
        
        self.yard_15_check = QCheckBox("15 Yards")
        self.yard_15_check.setStyleSheet("color: #ffffff;")
        self.yard_15_check.stateChanged.connect(self.on_yard_type_changed)
        row3.addWidget(self.yard_15_check)
        
        self.yard_22_check = QCheckBox("22 Yards")
        self.yard_22_check.setStyleSheet("color: #ffffff;")
        self.yard_22_check.stateChanged.connect(self.on_yard_type_changed)
        row3.addWidget(self.yard_22_check)
        
        row3.addStretch()
        filter_layout.addLayout(row3)
        
        # Row 4: Amount Type
        row4 = QHBoxLayout()
        row4.setSpacing(10)
        
        amount_label = QLabel("Amount Type:")
        amount_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        amount_label.setMinimumWidth(130)
        row4.addWidget(amount_label)
        
        self.amount_debit_check = QCheckBox("Debit")
        self.amount_debit_check.setStyleSheet("color: #ffffff;")
        self.amount_debit_check.stateChanged.connect(self.on_filter_changed)
        row4.addWidget(self.amount_debit_check)
        
        self.amount_credit_check = QCheckBox("Credit")
        self.amount_credit_check.setStyleSheet("color: #ffffff;")
        self.amount_credit_check.stateChanged.connect(self.on_filter_changed)
        row4.addWidget(self.amount_credit_check)
        
        row4.addStretch()
        
        # Clear Filters Button
        clear_btn = QPushButton("🗑️ Clear Filters")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                border: 1px solid #b71c1c;
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        clear_btn.clicked.connect(self.clear_filters)
        row4.addWidget(clear_btn)
        
        filter_layout.addLayout(row4)
        filter_group.setLayout(filter_layout)
        filters_layout.addWidget(filter_group)
        
        # Generate Report Button
        button_row = QHBoxLayout()
        button_row.addStretch()
        
        self.generate_report_btn = QPushButton("📊 Generate Report")
        self.generate_report_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                border: 1px solid #005a9e;
                border-radius: 6px;
                padding: 12px 30px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        self.generate_report_btn.clicked.connect(self.generate_report)
        button_row.addWidget(self.generate_report_btn)
        
        filters_layout.addLayout(button_row)
        
        # Set layout to card container
        card_container.setLayout(filters_layout)
        
        # Center the card horizontally
        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(card_container)
        center_layout.addStretch()
        
        # Add centered card to outer layout
        outer_layout.addLayout(center_layout)
        
        # Add stretch at bottom for centering
        outer_layout.addStretch()
        
        filters_widget.setLayout(outer_layout)
        return filters_widget
    
    def create_table_view(self):
        """Create the table view widget"""
        table_widget = QWidget()
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(15)
        
        # Header with Back button and Print button
        header = QHBoxLayout()
        
        self.back_btn = QPushButton("← Back to Filters")
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        self.back_btn.clicked.connect(self.show_filters_view)
        header.addWidget(self.back_btn)
        
        title = QLabel("📋 Stock Ledger Report")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)
        header.addStretch()
        
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
        self.print_btn.clicked.connect(self.print_ledger_report)
        header.addWidget(self.print_btn)
        
        table_layout.addLayout(header)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Date", "Transaction\nType", "Particulars", "Description",
            "Item Name", "15 Yard\nQty", "22 Yard\nQty",
            "Total Qty\n(Debit)", "Total Qty\n(Credit)", "Balance"
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
            QHeaderView::section {
                background-color: #2d2d2d;
                padding: 10px 8px;
                border: none;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        self.table.setAlternatingRowColors(True)
        # Set column widths
        self.table.setColumnWidth(0, 100)  # Date
        self.table.setColumnWidth(1, 120)  # Transaction Type
        self.table.setColumnWidth(2, 150)  # Particulars
        self.table.setColumnWidth(3, 200)  # Description
        self.table.setColumnWidth(4, 150)  # Item Name
        self.table.setColumnWidth(5, 100)  # 15 Yard Qty
        self.table.setColumnWidth(6, 100)  # 22 Yard Qty
        self.table.setColumnWidth(7, 120)  # Total Qty Debit
        self.table.setColumnWidth(8, 120)  # Total Qty Credit
        # Balance will stretch
        table_layout.addWidget(self.table)
        
        table_widget.setLayout(table_layout)
        return table_widget
    
    def load_ledgers(self):
        """Load all available ledgers"""
        try:
            response = self.api_client._try_request("GET", "/api/stock-ledgers")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    ledgers = data.get("ledgers", [])
                    self.ledger_combo.clear()
                    self.ledger_combo.addItem("-- Select Ledger --", None)
                    for ledger in ledgers:
                        display_name = ledger.get('ledger_name', '')
                        if ledger.get('is_ud_ledger'):
                            display_name = f"🌟 {display_name}"
                        self.ledger_combo.addItem(display_name, ledger.get('id'))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load ledgers: {str(e)}")
            self.server_available = False
    
    def on_ledger_activated(self, index):
        """Handle when user explicitly selects a ledger from dropdown"""
        if index < 0 or index >= self.ledger_combo.count():
            return
        
        ledger_id = self.ledger_combo.itemData(index)
        if ledger_id:
            # Update the line edit text to match the selected item
            selected_text = self.ledger_combo.itemText(index)
            self.ledger_combo.lineEdit().setText(selected_text)
            
            # Update ledger ID
            self.current_ledger_id = ledger_id
            # Clear previous entries when ledger changes
            self.all_entries = []
            self.filtered_entries = []
            if self.current_view == 'table':
                self.table.setRowCount(0)
            
            # Load entries in background to populate filter dropdowns
            # This allows filter suggestions to appear immediately
            self.load_ledger_entries()
        else:
            # Placeholder or invalid selection
            self.current_ledger_id = None
            self.all_entries = []
            self.filtered_entries = []
            # Clear filter dropdowns
            self.trans_type_combo.clear()
            self.trans_type_combo.addItem("")
            self.item_combo.clear()
            self.item_combo.addItem("")
            if self.current_view == 'table':
                self.table.setRowCount(0)
    
    def on_ledger_selected(self, index):
        """Handle when ledger is selected (handles programmatic changes)"""
        # Only process if index is valid
        if index < 0 or index >= self.ledger_combo.count():
            return
        
        # Get ledger ID from the item data
        ledger_id = self.ledger_combo.itemData(index)
        
        # Only update if the ledger ID has changed and is valid
        if ledger_id and ledger_id != self.current_ledger_id:
            # Update the line edit text to match the selected item
            selected_text = self.ledger_combo.itemText(index)
            self.ledger_combo.lineEdit().setText(selected_text)
            
            # Update ledger ID
            self.current_ledger_id = ledger_id
            # Clear previous entries when ledger changes
            self.all_entries = []
            self.filtered_entries = []
            if self.current_view == 'table':
                self.table.setRowCount(0)
            
            # Load entries in background to populate filter dropdowns
            # This allows filter suggestions to appear immediately
            self.load_ledger_entries()
        elif not ledger_id:
            # Placeholder selected or no valid data
            if self.current_ledger_id is not None:
                self.current_ledger_id = None
                self.all_entries = []
                self.filtered_entries = []
                # Clear filter dropdowns
                self.trans_type_combo.clear()
                self.trans_type_combo.addItem("")
                self.item_combo.clear()
                self.item_combo.addItem("")
                if self.current_view == 'table':
                    self.table.setRowCount(0)
    
    def load_ledger_entries(self):
        """Load entries for the selected ledger"""
        if not self.current_ledger_id:
            return
        
        # Cancel and wait for previous loader if it's still running
        if self.current_loader and self.current_loader.isRunning():
            self.current_loader.cancel()
            self.current_loader.wait(2000)  # Wait up to 2 seconds for graceful shutdown
            if self.current_loader.isRunning():
                # If still running, terminate it
                self.current_loader.terminate()
                self.current_loader.wait(1000)  # Wait for termination
        
        # Disconnect previous loader signals to prevent stale callbacks
        if self.current_loader:
            try:
                self.current_loader.finished.disconnect()
                self.current_loader.error.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.current_loader.deleteLater()  # Schedule for deletion
            self.current_loader = None
        
        # Create and start new loader
        self.current_loader = LedgerLoader(self.api_client, self.current_ledger_id)
        self.current_loader.finished.connect(self.on_entries_loaded)
        self.current_loader.error.connect(self.on_load_error)
        self.current_loader.start()
    
    def on_entries_loaded(self, entries):
        """Handle when entries are loaded - populate dropdowns and optionally switch to table"""
        self.populate_table(entries)
        # Only switch to table view if we were generating a report
        # If we're just loading entries for filter dropdowns, stay in filters view
        # (Don't auto-switch - user must click Generate Report)
    
    def closeEvent(self, event):
        """Clean up threads when widget is closed"""
        if self.current_loader and self.current_loader.isRunning():
            self.current_loader.cancel()
            self.current_loader.wait(2000)
            if self.current_loader.isRunning():
                self.current_loader.terminate()
                self.current_loader.wait(1000)
        super().closeEvent(event)
    
    def populate_table(self, entries):
        """Populate table with ledger entries"""
        # Store all entries for filtering
        self.all_entries = entries
        
        # Extract unique values for dropdowns
        self.update_filter_dropdowns()
        
        # Only apply filters if we're in table view
        if self.current_view == 'table':
            self.apply_filters()
        # If in filters view, just store the entries (don't filter yet)
    
    def update_filter_dropdowns(self):
        """Extract unique values from entries and populate dropdowns"""
        if not self.all_entries:
            return
        
        # Extract unique transaction types/numbers
        trans_types = set()
        items = set()
        particulars = set()
        
        for entry in self.all_entries:
            # Transaction type - use transaction_number if available, else transaction_type
            trans_number = entry.get('transaction_number', '')
            trans_type = entry.get('transaction_type', '')
            if trans_number:
                trans_types.add(trans_number)
            elif trans_type:
                trans_types.add(trans_type)
            
            # Items
            item_name = entry.get('item_name', '')
            if item_name:
                items.add(item_name)
            
            # Particulars
            particular = entry.get('particulars', '')
            if particular:
                particulars.add(particular)
        
        # Update transaction type combo
        current_trans_text = self.trans_type_combo.currentText()
        self.trans_type_combo.clear()
        self.trans_type_combo.addItem("")  # Empty option for "all"
        for trans_type in sorted(trans_types):
            self.trans_type_combo.addItem(trans_type)
        # Restore previous selection if it still exists
        index = self.trans_type_combo.findText(current_trans_text)
        if index >= 0:
            self.trans_type_combo.setCurrentIndex(index)
        else:
            self.trans_type_combo.setCurrentIndex(0)
            self.trans_type_combo.setEditText("")  # Clear edit text
        
        # Update completer model for transaction type (refresh it)
        if hasattr(self, 'trans_type_completer'):
            self.trans_type_completer.setModel(self.trans_type_combo.model())
        
        # Update item combo
        current_item_text = self.item_combo.currentText()
        self.item_combo.clear()
        self.item_combo.addItem("")  # Empty option for "all"
        for item in sorted(items):
            self.item_combo.addItem(item)
        # Restore previous selection if it still exists
        index = self.item_combo.findText(current_item_text)
        if index >= 0:
            self.item_combo.setCurrentIndex(index)
        else:
            self.item_combo.setCurrentIndex(0)
            self.item_combo.setEditText("")  # Clear edit text
        
        # Update completer model for item (refresh it)
        if hasattr(self, 'item_completer'):
            self.item_completer.setModel(self.item_combo.model())
        
        # Update particulars combo
        current_particulars_text = self.particulars_filter.currentText()
        self.particulars_filter.clear()
        self.particulars_filter.addItem("")  # Empty option for "all"
        for particular in sorted(particulars):
            self.particulars_filter.addItem(particular)
        # Restore previous selection if it still exists
        index = self.particulars_filter.findText(current_particulars_text)
        if index >= 0:
            self.particulars_filter.setCurrentIndex(index)
        else:
            self.particulars_filter.setCurrentIndex(0)
            self.particulars_filter.setEditText("")  # Clear edit text
        
        # Update completer model for particulars (refresh it)
        if hasattr(self, 'particulars_completer'):
            self.particulars_completer.setModel(self.particulars_filter.model())
    
    def apply_filters(self):
        """Apply all active filters to the entries"""
        if not self.all_entries:
            self.filtered_entries = []
            if self.current_view == 'table':
                self.table.setRowCount(0)
            return
        
        filtered_entries = self.all_entries.copy()
        
        # Date Range Filter
        from_date = self.from_date_edit.date().toPyDate()
        to_date = self.to_date_edit.date().toPyDate()
        
        # Transaction Type Filter
        trans_type_filter = self.trans_type_combo.currentText().strip()
        
        # Particulars Filter
        particulars_filter = self.particulars_filter.currentText().strip().lower()
        
        # Item Filter
        item_filter = self.item_combo.currentText().strip()
        
        # Yard Filter
        yard_15_selected = self.yard_15_check.isChecked()
        yard_22_selected = self.yard_22_check.isChecked()
        
        # Amount Type Filter
        debit_selected = self.amount_debit_check.isChecked()
        credit_selected = self.amount_credit_check.isChecked()
        
        # Apply filters
        result = []
        for entry in filtered_entries:
            # Date range filter
            entry_date_str = entry.get('entry_date', '')
            if entry_date_str:
                try:
                    if isinstance(entry_date_str, str):
                        if len(entry_date_str) >= 10:
                            entry_date = datetime.strptime(entry_date_str[:10], '%Y-%m-%d').date()
                        else:
                            continue
                    else:
                        entry_date = entry_date_str if hasattr(entry_date_str, 'date') else None
                        if entry_date:
                            entry_date = entry_date.date() if hasattr(entry_date, 'date') else entry_date
                    
                    if entry_date < from_date or entry_date > to_date:
                        continue
                except:
                    continue
            
            # Transaction type filter
            if trans_type_filter:
                trans_number = entry.get('transaction_number', '')
                trans_type = entry.get('transaction_type', '')
                trans_display = trans_number if trans_number else trans_type
                if trans_type_filter.lower() not in trans_display.lower():
                    continue
            
            # Particulars filter
            if particulars_filter:
                particulars = entry.get('particulars', '').lower()
                if particulars_filter not in particulars:
                    continue
            
            # Item filter
            if item_filter:
                item_name = entry.get('item_name', '')
                if item_filter.lower() not in item_name.lower():
                    continue
            
            # Yard type filter
            if yard_15_selected or yard_22_selected:
                qty_15 = float(entry.get('qty_15_yards', 0) or 0)
                qty_22 = float(entry.get('qty_22_yards', 0) or 0)
                
                if yard_15_selected and yard_22_selected:
                    # Both selected - show entries with either
                    if qty_15 == 0 and qty_22 == 0:
                        continue
                elif yard_15_selected:
                    # Only 15 yards - show only where 22-yard = 0
                    if qty_22 != 0:
                        continue
                elif yard_22_selected:
                    # Only 22 yards - show only where 15-yard = 0
                    if qty_15 != 0:
                        continue
            
            # Amount type filter
            if debit_selected or credit_selected:
                debit = float(entry.get('total_qty_debit', 0) or 0)
                credit = float(entry.get('total_qty_credit', 0) or 0)
                
                if debit_selected and credit_selected:
                    # Both selected - show all
                    pass
                elif debit_selected:
                    # Only debit - show only debit entries
                    if debit == 0:
                        continue
                elif credit_selected:
                    # Only credit - show only credit entries
                    if credit == 0:
                        continue
            
            result.append(entry)
        
        # Store filtered results
        self.filtered_entries = result
        
        # Display filtered results only if in table view
        if self.current_view == 'table':
            self.display_entries(result)
    
    def display_entries(self, entries):
        """Display entries in the table"""
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            # Date
            date_str = entry.get('entry_date', '')
            if date_str and len(date_str) >= 10:
                date_str = date_str[:10]  # Get YYYY-MM-DD part
            self.table.setItem(row, 0, QTableWidgetItem(date_str))
            
            # Transaction Type - Show transaction number (e.g., IN-000001, OUT-000001)
            transaction_number = entry.get('transaction_number', '')
            transaction_type_display = transaction_number if transaction_number else entry.get('transaction_type', '')
            self.table.setItem(row, 1, QTableWidgetItem(transaction_type_display))
            
            # Particulars
            self.table.setItem(row, 2, QTableWidgetItem(entry.get('particulars', '')))
            
            # Description
            self.table.setItem(row, 3, QTableWidgetItem(entry.get('description', '')))
            
            # Item Name
            self.table.setItem(row, 4, QTableWidgetItem(entry.get('item_name', '')))
            
            # 15 Yard Qty
            self.table.setItem(row, 5, QTableWidgetItem(str(entry.get('qty_15_yards', 0))))
            
            # 22 Yard Qty
            self.table.setItem(row, 6, QTableWidgetItem(str(entry.get('qty_22_yards', 0))))
            
            # Total Qty Debit
            debit = entry.get('total_qty_debit', 0)
            debit_item = QTableWidgetItem(str(debit))
            if debit > 0:
                debit_item.setForeground(Qt.green)
            self.table.setItem(row, 7, debit_item)
            
            # Total Qty Credit
            credit = entry.get('total_qty_credit', 0)
            credit_item = QTableWidgetItem(str(credit))
            if credit > 0:
                credit_item.setForeground(Qt.red)
            self.table.setItem(row, 8, credit_item)
            
            # Balance
            balance = entry.get('balance', 0)
            balance_item = QTableWidgetItem(str(balance))
            if balance < 0:
                balance_item.setForeground(Qt.red)
            elif balance == 0:
                balance_item.setForeground(Qt.yellow)
            else:
                balance_item.setForeground(Qt.green)
            self.table.setItem(row, 9, balance_item)
    
    def on_yard_type_changed(self, state):
        """Handle yard type checkbox changes - ensure mutual exclusivity"""
        sender = self.sender()
        if sender == self.yard_15_check and state == Qt.Checked:
            self.yard_22_check.setChecked(False)
        elif sender == self.yard_22_check and state == Qt.Checked:
            self.yard_15_check.setChecked(False)
        # Trigger filter change handler
        self.on_filter_changed()
    
    def on_filter_changed(self):
        """Handle filter changes - apply filters only if in table view"""
        if self.current_view == 'table' and self.all_entries:
            self.apply_filters()
    
    def clear_filters(self):
        """Clear all filters and reset to default view"""
        # Reset date range to default (1 year ago to today)
        self.from_date_edit.setDate(QDate.currentDate().addYears(-1))
        self.to_date_edit.setDate(QDate.currentDate())
        
        # Clear transaction type
        self.trans_type_combo.setCurrentIndex(0)
        
        # Clear particulars
        self.particulars_filter.setCurrentIndex(0)
        self.particulars_filter.setEditText("")
        
        # Clear item
        self.item_combo.setCurrentIndex(0)
        
        # Clear yard type
        self.yard_15_check.setChecked(False)
        self.yard_22_check.setChecked(False)
        
        # Clear amount type
        self.amount_debit_check.setChecked(False)
        self.amount_credit_check.setChecked(False)
        
        # Only apply filters if in table view
        if self.current_view == 'table':
            self.apply_filters()
    
    def show_filters_view(self):
        """Switch to filters view - preserves all filter values"""
        self.current_view = 'filters'
        self.stacked_widget.setCurrentIndex(0)  # Filters view is index 0
    
    def show_table_view(self):
        """Switch to table view - shows filtered results"""
        self.current_view = 'table'
        self.stacked_widget.setCurrentIndex(1)  # Table view is index 1
        # Apply filters when showing table view to display results
        if self.all_entries:
            self.apply_filters()
        elif self.filtered_entries:
            # If we have filtered entries from before, show them
            self.display_entries(self.filtered_entries)
    
    def showEvent(self, event):
        """Restore view state when module becomes visible"""
        super().showEvent(event)
        # Restore the last view state
        if self.current_view == 'table':
            self.stacked_widget.setCurrentIndex(1)
        else:
            self.stacked_widget.setCurrentIndex(0)
    
    def generate_report(self):
        """Generate report: load entries if needed, then show table view"""
        # Check if ledger is selected
        if not self.current_ledger_id:
            QMessageBox.warning(self, "No Ledger Selected", "Please select a ledger before generating the report.")
            return
        
        # If we don't have entries yet, load them
        if not self.all_entries:
            self.load_ledger_entries()
            # The populate_table will be called when loading finishes
            # We'll switch to table view there
            return
        
        # We have entries, switch to table view and apply filters
        self.show_table_view()
    
    def on_load_error(self, error):
        QMessageBox.warning(self, "Error", f"Failed to load ledger entries: {error}")
        self.server_available = False

    def print_ledger_report(self):
        """Print the current ledger report"""
        if not self.filtered_entries:
            QMessageBox.warning(self, "No Data", "No ledger entries to print. Please generate a report first.")
            return
        
        try:
            # Get ledger name
            ledger_name = "Unknown Ledger"
            if self.current_ledger_id:
                for i in range(self.ledger_combo.count()):
                    if self.ledger_combo.itemData(i) == self.current_ledger_id:
                        ledger_name = self.ledger_combo.itemText(i).replace("🌟 ", "")
                        break
            
            html_content = self.generate_ledger_print_html(self.filtered_entries, ledger_name)
            
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
    
    def _get_filter_display(self, filter_type):
        """Get display text for a filter"""
        if filter_type == 'particulars':
            value = self.particulars_filter.currentText().strip()
            return value if value else "All"
        elif filter_type == 'item':
            value = self.item_combo.currentText().strip()
            return value if value else "All"
        elif filter_type == 'transaction':
            value = self.trans_type_combo.currentText().strip()
            return value if value else "All"
        elif filter_type == 'yards':
            yard_15 = self.yard_15_check.isChecked()
            yard_22 = self.yard_22_check.isChecked()
            if yard_15 and yard_22:
                return "15 Yards, 22 Yards"
            elif yard_15:
                return "15 Yards"
            elif yard_22:
                return "22 Yards"
            else:
                return "All"
        elif filter_type == 'amount':
            debit = self.amount_debit_check.isChecked()
            credit = self.amount_credit_check.isChecked()
            if debit and credit:
                return "Debit, Credit"
            elif debit:
                return "Debit"
            elif credit:
                return "Credit"
            else:
                return "All"
        return "All"
    
    def generate_ledger_print_html(self, entries, ledger_name):
        """Generate print-ready HTML for ledger report"""
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
        
        # Get date range from filters
        from_date = self.from_date_edit.date().toString('dd-MM-yyyy')
        to_date = self.to_date_edit.date().toString('dd-MM-yyyy')
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Stock Ledger Report</title>
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
    
    <div class="report-title">STOCK LEDGER REPORT</div>
    
    <div class="report-info">
        <table>
            <tr>
                <td><strong>Ledger:</strong> {ledger_name}</td>
                <td><strong>Date Range:</strong> {from_date} to {to_date}</td>
            </tr>
            <tr>
                <td><strong>Total Entries:</strong> {len(entries)}</td>
                <td><strong>Generated:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</td>
            </tr>
        </table>
    </div>
    
    <div class="report-info">
        <table>
            <tr>
                <td><strong>Filters Applied:</strong></td>
                <td></td>
            </tr>
            <tr>
                <td><strong>Particular:</strong> {self._get_filter_display('particulars')}</td>
                <td><strong>Item:</strong> {self._get_filter_display('item')}</td>
            </tr>
            <tr>
                <td><strong>Transaction:</strong> {self._get_filter_display('transaction')}</td>
                <td><strong>Yards:</strong> {self._get_filter_display('yards')}</td>
            </tr>
            <tr>
                <td><strong>Debit/Credit:</strong> {self._get_filter_display('amount')}</td>
                <td></td>
            </tr>
        </table>
    </div>
    
    <table>
        <thead>
            <tr>
                <th style="width: 8%;">Date</th>
                <th style="width: 12%;">Transaction Type</th>
                <th style="width: 12%;">Particulars</th>
                <th style="width: 15%;">Description</th>
                <th style="width: 12%;">Item Name</th>
                <th style="width: 8%;">15 Yard Qty</th>
                <th style="width: 8%;">22 Yard Qty</th>
                <th style="width: 10%;" class="text-right">Debit</th>
                <th style="width: 10%;" class="text-right">Credit</th>
                <th style="width: 5%;" class="text-right">Balance</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for entry in entries:
            date_str = entry.get('entry_date', '')
            if date_str and len(date_str) >= 10:
                date_str = date_str[:10]
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    formatted_date = date_obj.strftime('%d-%m-%Y')
                except:
                    formatted_date = date_str
            else:
                formatted_date = ''
            
            transaction_number = entry.get('transaction_number', '')
            transaction_type_display = transaction_number if transaction_number else entry.get('transaction_type', '')
            
            html += f"""
            <tr>
                <td>{formatted_date}</td>
                <td>{transaction_type_display}</td>
                <td>{entry.get('particulars', '')}</td>
                <td>{entry.get('description', '')}</td>
                <td>{entry.get('item_name', '')}</td>
                <td class="text-right">{entry.get('qty_15_yards', 0)}</td>
                <td class="text-right">{entry.get('qty_22_yards', 0)}</td>
                <td class="text-right">{entry.get('total_qty_debit', 0)}</td>
                <td class="text-right">{entry.get('total_qty_credit', 0)}</td>
                <td class="text-right">{entry.get('balance', 0)}</td>
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