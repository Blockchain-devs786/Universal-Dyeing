"""Cash Ledgers Module - View financial ledger entries for Parties and Default Accounts"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QAbstractItemView,
    QMessageBox, QDateEdit, QGroupBox, QCheckBox, QStackedWidget, QCalendarWidget
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal, QUrl, QSize
from PyQt5.QtGui import QFont, QDesktopServices, QColor
from client.api_client import APIClient
from datetime import datetime
import os
import base64
import tempfile
import webbrowser
from common.config import CLIENT_FALLBACK_SERVER


class FinancialLedgerLoader(QThread):
    """Thread to load financial ledger entries asynchronously"""
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
            
            response = self.api_client._try_request("GET", f"/api/financial-ledgers/{self.ledger_id}/entries")
            
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


class CashLedgersModule(QWidget):
    """Cash Ledgers Module - View financial ledger entries"""
    
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data
        self.api_client = APIClient()
        self.current_ledger_id = None
        self.current_loader = None
        self.all_entries = []
        self.current_view = 'filters'
        self.filtered_entries = []
        
        self.init_ui()
        self.load_ledgers()
        self.show_filters_view()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        self.stacked_widget = QStackedWidget()
        self.filters_view = self.create_filters_view()
        self.stacked_widget.addWidget(self.filters_view)
        
        self.table_view = self.create_table_view()
        self.stacked_widget.addWidget(self.table_view)
        
        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)
    
    def create_filters_view(self):
        filters_widget = QWidget()
        outer_layout = QVBoxLayout()
        outer_layout.addStretch()
        
        card_container = QWidget()
        card_container.setMaximumWidth(900)
        card_container.setMinimumWidth(700)
        card_container.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border: 2px solid #3d3d3d;
                border-radius: 12px;
                padding: 40px;
            }
        """)
        
        filters_layout = QVBoxLayout()
        filters_layout.setSpacing(20)
        
        header = QHBoxLayout()
        title = QLabel("💰 Cash Ledgers")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)
        header.addStretch()
        
        search_label = QLabel("Select Ledger:")
        search_label.setStyleSheet("color: #ffffff;")
        header.addWidget(search_label)
        
        self.ledger_combo = QComboBox()
        self.ledger_combo.setMinimumWidth(300)
        self.ledger_combo.setEditable(True)
        self.ledger_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
            }
        """)
        self.ledger_combo.currentIndexChanged.connect(self.on_ledger_selected)
        header.addWidget(self.ledger_combo)
        filters_layout.addLayout(header)
        
        info_label = QLabel("View financial transactions for parties and default accounts. Entries are automatically created from Invoices and Vouchers.")
        info_label.setStyleSheet("color: #888888; font-style: italic;")
        info_label.setWordWrap(True)
        filters_layout.addWidget(info_label)
        
        # Filters Group
        filter_group = QGroupBox("🔍 Filters")
        filter_group.setStyleSheet("QGroupBox { font-weight: bold; color: #ffffff; border: 2px solid #3d3d3d; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        filter_layout = QVBoxLayout()
        
        date_row = QHBoxLayout()
        date_row.addWidget(QLabel("Date Range:"))
        self.from_date_edit = CompactDateEdit()
        self.from_date_edit.setDate(QDate.currentDate().addMonths(-1))
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
        date_row.addWidget(QLabel("From:"))
        date_row.addWidget(self.from_date_edit)
        self.to_date_edit = CompactDateEdit()
        self.to_date_edit.setDate(QDate.currentDate())
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
        date_row.addWidget(QLabel("To:"))
        date_row.addWidget(self.to_date_edit)
        date_row.addStretch()
        filter_layout.addLayout(date_row)
        
        filter_group.setLayout(filter_layout)
        filters_layout.addWidget(filter_group)
        
        button_row = QHBoxLayout()
        button_row.addStretch()
        self.generate_report_btn = QPushButton("📊 Generate Report")
        self.generate_report_btn.setStyleSheet("QPushButton { background-color: #0078d4; color: white; padding: 12px 30px; font-weight: bold; border-radius: 6px; }")
        self.generate_report_btn.clicked.connect(self.generate_report)
        button_row.addWidget(self.generate_report_btn)
        filters_layout.addLayout(button_row)
        
        card_container.setLayout(filters_layout)
        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(card_container)
        center_layout.addStretch()
        outer_layout.addLayout(center_layout)
        outer_layout.addStretch()
        filters_widget.setLayout(outer_layout)
        return filters_widget
    
    def create_table_view(self):
        table_widget = QWidget()
        table_layout = QVBoxLayout()
        
        header = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        self.back_btn.clicked.connect(self.show_filters_view)
        header.addWidget(self.back_btn)
        
        self.report_title = QLabel("💰 Cash Ledger Report")
        self.report_title.setFont(QFont("Arial", 16, QFont.Bold))
        header.addWidget(self.report_title)
        header.addStretch()
        
        self.print_btn = QPushButton("🖨️ Print")
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.print_btn.clicked.connect(self.print_report)
        header.addWidget(self.print_btn)
        table_layout.addLayout(header)
        
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Date", "Particulars", "Invoice/Voucher", "Description",
            "Credit", "Debit", "Balance"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget { 
                background-color: #1e1e1e; 
                alternate-background-color: #2a2a2a;
                color: #ffffff; 
                gridline-color: #3d3d3d; 
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        table_layout.addWidget(self.table)
        
        table_widget.setLayout(table_layout)
        return table_widget
    
    def load_ledgers(self):
        try:
            # Load financial ledgers
            response = self.api_client._try_request("GET", "/api/financial-ledgers")
            financial_ledgers = []
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    financial_ledgers = data.get("ledgers", [])
            
            # Load assets
            response = self.api_client._try_request("GET", "/api/assets")
            assets = []
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    assets = data.get("assets", [])
            
            # Load liabilities (parties)
            response = self.api_client._try_request("GET", "/api/parties")
            liabilities = []
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    liabilities = [p for p in data.get("parties", []) if p.get('is_active', True)]
            
            # Load expenses
            response = self.api_client._try_request("GET", "/api/expenses")
            expenses = []
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    expenses = data.get("expenses", [])
            
            # Load vendors
            response = self.api_client._try_request("GET", "/api/vendors")
            vendors = []
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    vendors = data.get("vendors", [])
            
            # Clear and populate combo box
            self.ledger_combo.clear()
            self.ledger_combo.addItem("-- Select Ledger --", None)
            
            # Add default accounts (financial ledgers with is_default = True) with star icon
            for ledger in financial_ledgers:
                ledger_name = ledger.get('name', '')
                if 'Cash Ledger' not in ledger_name and ledger.get('is_default', False):
                    display_name = f"🌟 {ledger_name}"
                    self.ledger_combo.addItem(display_name, ledger['id'])
            
            # Add assets with "- assets" suffix
            for asset in assets:
                if asset.get('is_active', True):
                    asset_name = asset.get('name', '')
                    display_name = f"{asset_name} - assets"
                    # Find corresponding financial ledger for this asset
                    asset_ledger_id = None
                    for ledger in financial_ledgers:
                        if ledger.get('name') == asset_name and not ledger.get('is_default', False):
                            asset_ledger_id = ledger.get('id')
                            break
                    if asset_ledger_id:
                        self.ledger_combo.addItem(display_name, asset_ledger_id)
            
            # Add expenses with "- Expenses" suffix
            for expense in expenses:
                if expense.get('is_active', True):
                    expense_name = expense.get('name', '')
                    display_name = f"{expense_name} - Expenses"
                    # Find corresponding financial ledger for this expense
                    expense_ledger_id = None
                    for ledger in financial_ledgers:
                        if ledger.get('name') == expense_name and not ledger.get('is_default', False):
                            expense_ledger_id = ledger.get('id')
                            break
                    if expense_ledger_id:
                        self.ledger_combo.addItem(display_name, expense_ledger_id)
            
            # Add vendors with "- Vendors" suffix
            for vendor in vendors:
                if vendor.get('is_active', True):
                    vendor_name = vendor.get('name', '')
                    display_name = f"{vendor_name} - Vendors"
                    # Find corresponding financial ledger for this vendor
                    vendor_ledger_id = None
                    for ledger in financial_ledgers:
                        if ledger.get('name') == vendor_name and not ledger.get('is_default', False):
                            vendor_ledger_id = ledger.get('id')
                            break
                    if vendor_ledger_id:
                        self.ledger_combo.addItem(display_name, vendor_ledger_id)
            
            # Add liabilities (parties) with "- liabilities" suffix
            for liability in liabilities:
                liability_name = liability.get('name', '')
                display_name = f"{liability_name} - liabilities"
                # Find corresponding financial ledger for this liability
                liability_ledger_id = None
                for ledger in financial_ledgers:
                    if ledger.get('name') == liability_name and not ledger.get('is_default', False):
                        liability_ledger_id = ledger.get('id')
                        break
                if liability_ledger_id:
                    self.ledger_combo.addItem(display_name, liability_ledger_id)
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load ledgers: {str(e)}")
    
    def on_ledger_selected(self, index):
        ledger_id = self.ledger_combo.itemData(index)
        if ledger_id:
            self.current_ledger_id = ledger_id
            self.load_entries()
    
    def load_entries(self):
        if not self.current_ledger_id: return
        if self.current_loader and self.current_loader.isRunning():
            self.current_loader.cancel()
            self.current_loader.wait()
        
        self.current_loader = FinancialLedgerLoader(self.api_client, self.current_ledger_id)
        self.current_loader.finished.connect(self.on_entries_loaded)
        self.current_loader.error.connect(lambda e: QMessageBox.warning(self, "Error", e))
        self.current_loader.start()
    
    def on_entries_loaded(self, entries):
        self.all_entries = entries
        if self.current_view == 'table':
            self.apply_filters()
    
    def apply_filters(self):
        from_date = self.from_date_edit.date().toPyDate()
        to_date = self.to_date_edit.date().toPyDate()
        
        filtered = []
        for entry in self.all_entries:
            try:
                e_date = datetime.strptime(entry['entry_date'], '%Y-%m-%d').date()
                if from_date <= e_date <= to_date:
                    filtered.append(entry)
            except: continue
        
        self.filtered_entries = filtered
        self.display_entries(filtered)
    
    def display_entries(self, entries):
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            self.table.setItem(row, 0, QTableWidgetItem(entry['entry_date']))
            self.table.setItem(row, 1, QTableWidgetItem(entry['particulars']))
            
            doc_num = entry.get('invoice_number') or entry.get('voucher_number') or ""
            self.table.setItem(row, 2, QTableWidgetItem(doc_num))
            
            self.table.setItem(row, 3, QTableWidgetItem(entry['description']))
            
            credit = float(entry.get('credit', 0))
            credit_item = QTableWidgetItem(f"{credit:,.2f}")
            if credit > 0: credit_item.setForeground(Qt.red)
            self.table.setItem(row, 4, credit_item)
            
            debit = float(entry.get('debit', 0))
            debit_item = QTableWidgetItem(f"{debit:,.2f}")
            if debit > 0: debit_item.setForeground(Qt.green)
            self.table.setItem(row, 5, debit_item)
            
            balance = float(entry.get('balance', 0))
            balance_item = QTableWidgetItem(f"{balance:,.2f}")
            if balance == 0:
                balance_item.setForeground(QColor(255, 255, 0))  # Yellow
            elif balance < 0:
                balance_item.setForeground(Qt.red)
            else:
                balance_item.setForeground(Qt.green)
            self.table.setItem(row, 6, balance_item)

    def generate_report(self):
        if not self.current_ledger_id:
            QMessageBox.warning(self, "No Ledger", "Please select a ledger.")
            return
        
        # Update report title with selected ledger name (remove formatting)
        ledger_name = self.ledger_combo.currentText()
        if ledger_name and ledger_name != "-- Select Ledger --":
            # Remove star icon and suffix formatting for display
            display_name = ledger_name.replace("🌟 ", "")
            if " - assets" in display_name:
                display_name = display_name.replace(" - assets", "")
            elif " - liabilities" in display_name:
                display_name = display_name.replace(" - liabilities", "")
            self.report_title.setText(f"💰 {display_name}")
        else:
            self.report_title.setText("💰 Cash Ledger Report")
            
        self.current_view = 'table'
        self.stacked_widget.setCurrentIndex(1)
        self.apply_filters()

    def show_filters_view(self):
        self.current_view = 'filters'
        self.stacked_widget.setCurrentIndex(0)

    def print_report(self):
        """Generate and print cash ledger report"""
        if not self.current_ledger_id:
            QMessageBox.warning(self, "No Ledger", "Please select a ledger to print.")
            return
        
        if not self.filtered_entries:
            QMessageBox.warning(self, "No Data", "No entries to print. Please generate a report first.")
            return
        
        try:
            # Get ledger name
            ledger_name = self.ledger_combo.currentText()
            if ledger_name and ledger_name != "-- Select Ledger --":
                # Remove star icon and suffix formatting for display
                display_name = ledger_name.replace("🌟 ", "")
                if " - assets" in display_name:
                    display_name = display_name.replace(" - assets", "")
                elif " - liabilities" in display_name:
                    display_name = display_name.replace(" - liabilities", "")
                elif " - Expenses" in display_name:
                    display_name = display_name.replace(" - Expenses", "")
                elif " - Vendors" in display_name:
                    display_name = display_name.replace(" - Vendors", "")
            else:
                display_name = "Cash Ledger"
            
            # Get date range
            from_date = self.from_date_edit.date().toPyDate()
            to_date = self.to_date_edit.date().toPyDate()
            
            # Generate HTML
            html_content = self.generate_cash_ledger_print_html(display_name, self.filtered_entries, from_date, to_date)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(html_content)
                temp_file_path = temp_file.name
            
            # Open in Chrome
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            
            chrome_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
            
            if chrome_path:
                os.system(f'"{chrome_path}" --print-to-pdf --print-to-pdf-no-header "{temp_file_path}"')
                webbrowser.open(f"file://{temp_file_path}")
            else:
                webbrowser.open(f"file://{temp_file_path}")
        except Exception as e:
            error_msg = str(e)
            print(f"[CashLedgersModule] EXCEPTION in print_report: {type(e).__name__}: {error_msg}")
            QMessageBox.critical(self, "Error", f"Failed to generate print document: {error_msg}")
    
    def find_logo_file(self):
        """Find logo file in common locations"""
        logo_names = ['logo.png', 'logo.jpg', 'logo.jpeg', 'Logo.png', 'Logo.jpg', 'Logo.jpeg']
        search_paths = [
            os.path.join(os.path.dirname(__file__), '..', 'assets'),
            os.path.join(os.getcwd(), 'assets'),
            os.path.dirname(__file__)
        ]
        
        for search_path in search_paths:
            for logo_name in logo_names:
                logo_path = os.path.join(search_path, logo_name)
                if os.path.exists(logo_path):
                    return logo_path
        return None
    
    def generate_cash_ledger_print_html(self, ledger_name, entries, from_date, to_date):
        """Generate print-ready HTML for cash ledger report"""
        logo_path = self.find_logo_file()
        logo_html = ""
        if logo_path:
            try:
                with open(logo_path, 'rb') as logo_file:
                    logo_data = logo_file.read()
                    logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                    logo_ext = os.path.splitext(logo_path)[1].lower()
                    mime_type = f'image/{logo_ext[1:]}' if logo_ext else 'image/png'
                    logo_html = f'<img src="data:{mime_type};base64,{logo_base64}" alt="Logo" style="background: transparent; width: 100%; height: 100%; object-fit: contain;" />'
            except:
                logo_html = f'<img src="{logo_path}" alt="Logo" style="background: transparent; width: 100%; height: 100%; object-fit: contain;" />'
        
        # Separate opening balance entries from regular entries
        opening_balance_entries = []
        regular_entries = []
        
        for entry in entries:
            description = entry.get('description', '').strip().upper()
            if description == "OPENING BALANCE":
                opening_balance_entries.append(entry)
            else:
                regular_entries.append(entry)
        
        # Calculate opening balance from opening balance entries
        opening_balance = 0
        for entry in opening_balance_entries:
            debit = float(entry.get('debit', 0) or 0)
            credit = float(entry.get('credit', 0) or 0)
            opening_balance += debit - credit
        
        # If no opening balance entries, calculate from first entry's balance
        if not opening_balance_entries and entries:
            first_entry = entries[0]
            first_balance = float(first_entry.get('balance', 0) or 0)
            first_debit = float(first_entry.get('debit', 0) or 0)
            first_credit = float(first_entry.get('credit', 0) or 0)
            opening_balance = first_balance - first_debit + first_credit
        
        # Calculate totals (including opening balance entries)
        total_debit = sum(float(entry.get('debit', 0) or 0) for entry in entries)
        total_credit = sum(float(entry.get('credit', 0) or 0) for entry in entries)
        closing_balance = float(entries[-1].get('balance', 0) or 0) if entries else 0
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Cash Ledger Report - {ledger_name}</title>
    <style>
        @page {{
            size: A4 landscape;
            margin: 10mm;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: Arial, sans-serif;
            font-size: 11px;
            background: white;
            padding: 0;
            color: #1a1a1a;
            margin: 0;
        }}
        
        .page {{
            width: 277mm;
            min-height: 190mm;
            page-break-after: always;
            position: relative;
            overflow: hidden;
        }}
        
        .page:last-child {{
            page-break-after: auto;
        }}
        
        .form {{
            width: 100%;
            height: 100%;
            border: 2px solid #0066cc;
            padding: 8mm;
            margin: 0;
            background: linear-gradient(to bottom, #f8f9fa, #ffffff);
            border-radius: 5px;
            page-break-inside: avoid;
            overflow: hidden;
            box-sizing: border-box;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 8mm;
            position: relative;
        }}
        
        .company-name {{
            font-size: 22px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 3mm;
            color: #0066cc;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }}
        
        .logo {{
            position: absolute;
            right: 0;
            top: 0;
            width: 50mm;
            height: 50mm;
            background: transparent;
        }}
        
        .subtitle-wrapper {{
            margin-right: 55mm;
            margin-bottom: 5mm;
        }}
        
        .subtitle {{
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            color: #0066cc;
            padding: 5px;
            background: linear-gradient(to right, #0066cc, #004499);
            color: white;
            border-radius: 3px;
        }}
        
        .meta-info {{
            background: #e8f4f8;
            border: 1px solid #0066cc;
            border-radius: 5px;
            padding: 5mm;
            margin-bottom: 5mm;
        }}
        
        .meta-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 3px;
            padding: 2px 0;
        }}
        
        .meta-label {{
            font-weight: bold;
            color: #0066cc;
            min-width: 120px;
        }}
        
        .meta-value {{
            flex: 1;
            text-align: left;
        }}
        
        .ledger-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 5mm;
            background: white;
            font-size: 10px;
        }}
        
        .ledger-table th {{
            background: linear-gradient(to right, #0066cc, #004499);
            color: white;
            padding: 6px;
            text-align: left;
            border: 1px solid #004499;
            font-weight: bold;
        }}
        
        .ledger-table td {{
            padding: 4px 6px;
            border: 1px solid #cccccc;
        }}
        
        .ledger-table tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        .total-row {{
            font-weight: bold;
            background: #e8f4f8 !important;
            border-top: 2px solid #0066cc;
        }}
        
        .footer {{
            margin-top: 10mm;
            text-align: center;
            font-size: 10px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="page">
        <div class="form">
            <div class="header">
                <div class="company-name">MOMINA LACE DYEING</div>
                <div class="logo">{logo_html}</div>
            </div>
            
            <div class="subtitle-wrapper">
                <div class="subtitle">CASH LEDGER REPORT</div>
            </div>
            
            <div class="meta-info">
                <div class="meta-row">
                    <span class="meta-label">LEDGER NAME:</span>
                    <span class="meta-value">{ledger_name}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">FROM DATE:</span>
                    <span class="meta-value">{from_date.strftime('%Y-%m-%d')}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">TO DATE:</span>
                    <span class="meta-value">{to_date.strftime('%Y-%m-%d')}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">OPENING BALANCE:</span>
                    <span class="meta-value">{opening_balance:,.2f}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">CLOSING BALANCE:</span>
                    <span class="meta-value">{closing_balance:,.2f}</span>
                </div>
            </div>
            
            <table class="ledger-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Particulars</th>
                        <th>Invoice/Voucher</th>
                        <th>Description</th>
                        <th style="text-align: right;">Credit</th>
                        <th style="text-align: right;">Debit</th>
                        <th style="text-align: right;">Balance</th>
                    </tr>
                </thead>
                <tbody>"""
        
        # Display opening balance entry if exists
        if opening_balance_entries:
            for entry in opening_balance_entries:
                date_str = entry.get('entry_date', '')[:10] if entry.get('entry_date') else ''
                particulars = entry.get('particulars', '')
                doc_num = entry.get('invoice_number') or entry.get('voucher_number') or ''
                description = entry.get('description', '')
                credit = float(entry.get('credit', 0) or 0)
                debit = float(entry.get('debit', 0) or 0)
                balance = float(entry.get('balance', 0) or 0)
                
                credit_str = f"{credit:,.2f}" if credit > 0 else ''
                debit_str = f"{debit:,.2f}" if debit > 0 else ''
                
                html += f"""
                    <tr style="background-color: #fff9e6;">
                        <td>{date_str}</td>
                        <td><strong>{particulars}</strong></td>
                        <td>{doc_num}</td>
                        <td><strong>{description}</strong></td>
                        <td style="text-align: right;">{credit_str}</td>
                        <td style="text-align: right;">{debit_str}</td>
                        <td style="text-align: right;"><strong>{balance:,.2f}</strong></td>
                    </tr>"""
        
        # Display regular entries
        for entry in regular_entries:
            date_str = entry.get('entry_date', '')[:10] if entry.get('entry_date') else ''
            particulars = entry.get('particulars', '')
            doc_num = entry.get('invoice_number') or entry.get('voucher_number') or ''
            description = entry.get('description', '')
            credit = float(entry.get('credit', 0) or 0)
            debit = float(entry.get('debit', 0) or 0)
            balance = float(entry.get('balance', 0) or 0)
            
            credit_str = f"{credit:,.2f}" if credit > 0 else ''
            debit_str = f"{debit:,.2f}" if debit > 0 else ''
            
            html += f"""
                    <tr>
                        <td>{date_str}</td>
                        <td>{particulars}</td>
                        <td>{doc_num}</td>
                        <td>{description}</td>
                        <td style="text-align: right;">{credit_str}</td>
                        <td style="text-align: right;">{debit_str}</td>
                        <td style="text-align: right;">{balance:,.2f}</td>
                    </tr>"""
        
        html += f"""
                    <tr class="total-row">
                        <td colspan="4"><strong>TOTAL</strong></td>
                        <td style="text-align: right;"><strong>{total_credit:,.2f}</strong></td>
                        <td style="text-align: right;"><strong>{total_debit:,.2f}</strong></td>
                        <td style="text-align: right;"><strong>{closing_balance:,.2f}</strong></td>
                    </tr>
                </tbody>
            </table>
            
            <div class="footer">
                <div>SITE: Small Industrial State, Sargodha Road, Faisalabad</div>
                <div>CONTACTS: 0321-7651815, 0300-8651815, 0304-6166663, 0300-8636129</div>
            </div>
        </div>
    </div>
</body>
</html>"""
        return html
