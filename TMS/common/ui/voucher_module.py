"""Voucher Module - Create and manage accounting vouchers (CP, CR, JV)"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QLineEdit, QFormLayout,
    QDialogButtonBox, QMessageBox, QComboBox, QDoubleSpinBox, QDateEdit,
    QAbstractItemView, QCompleter, QCalendarWidget, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont
from client.api_client import APIClient
from datetime import datetime
import requests
import os
import tempfile
import webbrowser
import base64
from common.config import CLIENT_FALLBACK_SERVER


class CompactDateEdit(QDateEdit):
    """DateEdit with smaller calendar popup"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
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


class VoucherLoader(QThread):
    """Thread to load vouchers asynchronously"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, api_client, voucher_type=None):
        super().__init__()
        self.api_client = api_client
        self.voucher_type = voucher_type
        self._is_cancelled = False
    
    def cancel(self):
        """Cancel the loading operation"""
        self._is_cancelled = True
    
    def run(self):
        try:
            if self._is_cancelled:
                return
            
            url = "/api/vouchers"
            if self.voucher_type:
                url += f"?voucher_type={self.voucher_type}"
            
            response = self.api_client._try_request("GET", url)
            
            if self._is_cancelled:
                return
            
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    if not self._is_cancelled:
                        self.finished.emit(data.get("vouchers", []))
                else:
                    if not self._is_cancelled:
                        self.error.emit(data.get("message", "Failed to load vouchers"))
            else:
                if not self._is_cancelled:
                    self.error.emit(f"Server returned status {response.status_code if response else 'No response'}")
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))


class VoucherModule(QWidget):
    """Voucher Management Module"""
    
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data
        self.api_client = APIClient()
        if user_data and user_data.get('username'):
            self.api_client.set_username(user_data.get('username'))
        self.all_vouchers = []
        self.current_loader = None
        self.init_ui()
        self.load_vouchers()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Vouchers")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Filter by type
        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet("color: #b0b0b0;")
        header.addWidget(filter_label)
        
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All", "CP", "CR", "JV"])
        self.type_filter.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
                min-width: 100px;
            }
            QComboBox:hover {
                border: 1px solid #0078d4;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.type_filter.currentTextChanged.connect(self.on_filter_changed)
        header.addWidget(self.type_filter)
        
        # Buttons
        self.add_btn = QPushButton("➕ Add Voucher")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.add_btn.clicked.connect(self.add_voucher)
        header.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                border: 1px solid #0078d4;
            }
        """)
        self.edit_btn.clicked.connect(self.edit_voucher)
        header.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_voucher)
        header.addWidget(self.delete_btn)
        
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
        self.print_btn.clicked.connect(self.print_vouchers)
        header.addWidget(self.print_btn)
        
        layout.addLayout(header)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Voucher No", "Type", "Date", "Description", "Amount", "Created"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        
        # Set column widths: Date smaller, Description larger
        self.table.setColumnWidth(0, 150)  # Voucher No
        self.table.setColumnWidth(1, 80)   # Type
        self.table.setColumnWidth(2, 100)  # Date (reduced)
        self.table.setColumnWidth(3, 400)  # Description (increased)
        self.table.setColumnWidth(4, 120)  # Amount
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                gridline-color: #3d3d3d;
                border: 1px solid #3d3d3d;
                alternate-background-color: #2a2a2a;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:alternate {
                background-color: #2a2a2a;
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
                background-color: #2a2a2a;
                color: #ffffff;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #0078d4;
            }
        """)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def on_filter_changed(self, text):
        """Handle filter change"""
        if text == "All":
            self.load_vouchers()
        else:
            self.load_vouchers(voucher_type=text)
    
    def load_vouchers(self, voucher_type=None):
        """Load vouchers from API"""
        if self.current_loader and self.current_loader.isRunning():
            self.current_loader.cancel()
        
        self.current_loader = VoucherLoader(self.api_client, voucher_type)
        self.current_loader.finished.connect(self.on_vouchers_loaded)
        self.current_loader.error.connect(self.on_load_error)
        self.current_loader.start()
    
    def on_vouchers_loaded(self, vouchers):
        """Handle vouchers loaded"""
        self.all_vouchers = vouchers
        self.populate_table()
    
    def on_load_error(self, error_msg):
        """Handle load error"""
        QMessageBox.warning(self, "Error", f"Failed to load vouchers: {error_msg}")
    
    def populate_table(self):
        """Populate table with vouchers"""
        self.table.setRowCount(len(self.all_vouchers))
        
        for row, voucher in enumerate(self.all_vouchers):
            self.table.setItem(row, 0, QTableWidgetItem(voucher.get('voucher_no', '')))
            self.table.setItem(row, 1, QTableWidgetItem(voucher.get('voucher_type', '')))
            
            date_str = voucher.get('voucher_date', '')
            if isinstance(date_str, str) and len(date_str) > 10:
                date_str = date_str[:10]
            self.table.setItem(row, 2, QTableWidgetItem(date_str))
            
            desc = voucher.get('description', '') or ''
            if len(desc) > 50:
                desc = desc[:50] + '...'
            self.table.setItem(row, 3, QTableWidgetItem(desc))
            
            amount = voucher.get('total_amount', 0) or 0
            self.table.setItem(row, 4, QTableWidgetItem(f"{amount:,.2f}"))
            
            created = voucher.get('created_at', '')
            if isinstance(created, str) and len(created) > 19:
                created = created[:19]
            self.table.setItem(row, 5, QTableWidgetItem(created))
    
    def add_voucher(self):
        """Show dialog to add new voucher"""
        dialog = VoucherDialog(self, user_data=self.user_data)
        if dialog.exec_() == QDialog.Accepted:
            self.load_vouchers()
    
    def edit_voucher(self):
        """Edit selected voucher"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a voucher to edit")
            return
        
        row = selected_rows[0].row()
        voucher = self.all_vouchers[row]
        voucher_id = voucher.get('id')
        
        dialog = VoucherDialog(self, user_data=self.user_data, voucher_id=voucher_id)
        if dialog.exec_() == QDialog.Accepted:
            self.load_vouchers()
    
    def delete_voucher(self):
        """Delete selected voucher"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a voucher to delete")
            return
        
        row = selected_rows[0].row()
        voucher = self.all_vouchers[row]
        voucher_id = voucher.get('id')
        voucher_no = voucher.get('voucher_no', '')
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete voucher {voucher_no}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                response = self.api_client._try_request_with_retry("DELETE", f"/api/vouchers/{voucher_id}")
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        QMessageBox.information(self, "Success", "Voucher deleted successfully")
                        self.load_vouchers()
                    else:
                        QMessageBox.warning(self, "Error", data.get("message", "Failed to delete voucher"))
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete voucher")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error deleting voucher: {str(e)}")
    
    def print_vouchers(self):
        """Show print dialog and print selected vouchers"""
        # Get selected rows
        selected_rows = self.table.selectionModel().selectedRows()
        selected_indices = set([row.row() for row in selected_rows])
        
        # Show print dialog
        dialog = PrintVoucherDialog(self, selected_indices, self.all_vouchers)
        if dialog.exec_() == QDialog.Accepted:
            selected_ids = dialog.get_selected_ids()
            if selected_ids:
                self.generate_and_print_html(selected_ids)
            else:
                QMessageBox.warning(self, "No Selection", "Please select at least one voucher to print")
    
    def generate_and_print_html(self, voucher_ids):
        """Generate HTML for printing and open in Chrome"""
        try:
            # Fetch all voucher documents
            vouchers = []
            for voucher_id in voucher_ids:
                try:
                    response = requests.get(
                        f"{CLIENT_FALLBACK_SERVER}/api/vouchers/{voucher_id}",
                        timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            vouchers.append(data.get("voucher"))
                except Exception as e:
                    error_msg = str(e)
                    print(f"[VoucherModule] ERROR loading voucher {voucher_id}: {type(e).__name__}: {error_msg}")
                    QMessageBox.warning(self, "Error", f"Failed to load voucher {voucher_id}: {error_msg}")
            
            if not vouchers:
                QMessageBox.warning(self, "Error", "No vouchers to print")
                return
            
            # Generate HTML
            html_content = self.generate_voucher_print_html(vouchers)
            
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
            print(f"[VoucherModule] EXCEPTION in generate_and_print_html: {type(e).__name__}: {error_msg}")
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
    
    def generate_voucher_print_html(self, vouchers):
        """Generate print-ready HTML for voucher documents"""
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
        
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Print Voucher Documents</title>
    <style>
        @page {
            size: A4 portrait;
            margin: 10mm;
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
            padding: 0;
            color: #1a1a1a;
            margin: 0;
        }
        
        .page {
            width: 190mm;
            min-height: 277mm;
            max-height: 277mm;
            page-break-after: always;
            position: relative;
            overflow: hidden;
        }
        
        .page:last-child {
            page-break-after: auto;
        }
        
        .form {
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
        }
        
        .header {
            text-align: center;
            margin-bottom: 8mm;
            position: relative;
        }
        
        .company-name {
            font-size: 22px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 3mm;
            color: #0066cc;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }
        
        .logo {
            position: absolute;
            right: 0;
            top: 0;
            width: 50mm;
            height: 50mm;
            background: transparent;
        }
        
        .subtitle-wrapper {
            margin-right: 55mm;
            margin-bottom: 5mm;
        }
        
        .subtitle {
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            color: #0066cc;
            padding: 5px;
            background: linear-gradient(to right, #0066cc, #004499);
            color: white;
            border-radius: 3px;
        }
        
        .meta-info {
            background: #e8f4f8;
            border: 1px solid #0066cc;
            border-radius: 5px;
            padding: 5mm;
            margin-bottom: 5mm;
        }
        
        .meta-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 3px;
            padding: 2px 0;
        }
        
        .meta-label {
            font-weight: bold;
            color: #0066cc;
            min-width: 120px;
        }
        
        .meta-value {
            flex: 1;
            text-align: left;
        }
        
        .details-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 5mm;
            background: white;
        }
        
        .details-table th {
            background: linear-gradient(to right, #0066cc, #004499);
            color: white;
            padding: 8px;
            text-align: left;
            border: 1px solid #004499;
            font-weight: bold;
        }
        
        .details-table td {
            padding: 6px 8px;
            border: 1px solid #cccccc;
        }
        
        .details-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        .total-row {
            font-weight: bold;
            background: #e8f4f8 !important;
            border-top: 2px solid #0066cc;
        }
        
        .footer {
            margin-top: 10mm;
            text-align: center;
            font-size: 10px;
            color: #666;
        }
    </style>
</head>
<body>"""
        
        for voucher in vouchers:
            # Build edit log history HTML if it exists
            edit_log_html = ''
            if voucher.get('edit_log_history'):
                edit_log_value = voucher.get('edit_log_history', 'None')
                edit_log_html = f'<div class="meta-row"><span class="meta-label">EDIT LOG HISTORY:</span><span class="meta-value" style="font-size: 10px;">{edit_log_value}</span></div>'
            
            voucher_type = voucher.get('voucher_type', '')
            voucher_type_name = {'CP': 'CASH PAYMENT', 'CR': 'CASH RECEIPT', 'JV': 'JOURNAL VOUCHER'}.get(voucher_type, voucher_type)
            
            html += f"""
    <div class="page">
        <div class="form">
            <div class="header">
                <div class="company-name">MOMINA LACE DYEING</div>
                <div class="logo">{logo_html}</div>
            </div>
            
            <div class="subtitle-wrapper">
                <div class="subtitle">{voucher_type_name}</div>
            </div>
            
            <div class="meta-info">
                <div class="meta-row">
                    <span class="meta-label">VOUCHER #:</span>
                    <span class="meta-value">{voucher.get('voucher_no', '')}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">DATE:</span>
                    <span class="meta-value">{voucher.get('voucher_date', '')[:10] if voucher.get('voucher_date') else ''}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">DESCRIPTION:</span>
                    <span class="meta-value">{voucher.get('description', '') or ''}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">CREATED BY:</span>
                    <span class="meta-value">{voucher.get('created_by', '') or 'None'}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">EDITED BY:</span>
                    <span class="meta-value">{voucher.get('edited_by', 'None') if voucher.get('edited_by') else 'None'}</span>
                </div>
                {edit_log_html}
            </div>
            
            <table class="details-table">
                <thead>
                    <tr>
                        <th>Account</th>
                        <th style="text-align: right;">Debit</th>
                        <th style="text-align: right;">Credit</th>
                    </tr>
                </thead>
                <tbody>"""
            
            total_debit = 0
            total_credit = 0
            for detail in voucher.get('details', []):
                account_name = detail.get('party_name') or detail.get('asset_name') or detail.get('expense_name') or detail.get('vendor_name') or 'Unknown'
                debit = float(detail.get('debit_amount', 0) or 0)
                credit = float(detail.get('credit_amount', 0) or 0)
                total_debit += debit
                total_credit += credit
                
                # Format debit and credit values
                debit_str = f"{debit:,.2f}" if debit > 0 else ''
                credit_str = f"{credit:,.2f}" if credit > 0 else ''
                
                html += f"""
                    <tr>
                        <td>{account_name}</td>
                        <td style="text-align: right;">{debit_str}</td>
                        <td style="text-align: right;">{credit_str}</td>
                    </tr>"""
            
            html += f"""
                    <tr class="total-row">
                        <td><strong>TOTAL</strong></td>
                        <td style="text-align: right;"><strong>{total_debit:,.2f}</strong></td>
                        <td style="text-align: right;"><strong>{total_credit:,.2f}</strong></td>
                    </tr>
                </tbody>
            </table>
            
            <div class="footer">
                <div>SITE: Small Industrial State, Sargodha Road, Faisalabad</div>
                <div>CONTACTS: 0321-7651815, 0300-8651815, 0304-6166663, 0300-8636129</div>
            </div>
        </div>
    </div>"""
        
        html += """
</body>
</html>"""
        return html


class PrintVoucherDialog(QDialog):
    """Dialog for selecting vouchers to print"""
    
    def __init__(self, parent, selected_rows, all_vouchers):
        super().__init__(parent)
        self.all_vouchers = all_vouchers
        self.selected_rows = selected_rows
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Print Vouchers")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel("Select vouchers to print:")
        label.setStyleSheet("color: #ffffff; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(label)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        
        # Populate list with all vouchers
        for idx, voucher in enumerate(self.all_vouchers):
            item_text = f"{voucher.get('voucher_no', '')} - {voucher.get('voucher_type', '')} - {voucher.get('voucher_date', '')[:10]}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, voucher.get('id'))
            
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
        
        print_btn = QPushButton("Print")
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        print_btn.clicked.connect(self.accept)
        button_layout.addWidget(print_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
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
        """Get list of selected voucher IDs"""
        selected_ids = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                voucher_id = item.data(Qt.UserRole)
                if voucher_id:
                    selected_ids.append(voucher_id)
        return selected_ids


class VoucherDialog(QDialog):
    """Dialog for creating/editing vouchers"""
    
    def __init__(self, parent=None, user_data=None, voucher_id=None):
        super().__init__(parent)
        self.user_data = user_data
        self.api_client = APIClient()
        if user_data and user_data.get('username'):
            self.api_client.set_username(user_data.get('username'))
        self.voucher_id = voucher_id
        self.is_edit_mode = voucher_id is not None
        self.voucher_type = None
        self.liabilities = []
        self.assets = []
        self.expenses = []
        self.vendors = []
        self.voucher_details = []
        
        self.setWindowTitle("Edit Voucher" if self.is_edit_mode else "Create Voucher")
        self.setMinimumSize(900, 700)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        self.init_ui()
        
        self.load_masters()
        if self.is_edit_mode:
            self.load_voucher_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Voucher type selection (only for new vouchers)
        if not self.is_edit_mode:
            type_layout = QHBoxLayout()
            type_label = QLabel("Voucher Type:")
            type_label.setStyleSheet("color: #b0b0b0;")
            type_layout.addWidget(type_label)
            
            self.type_combo = QComboBox()
            self.type_combo.addItems(["CP - Cash Payment", "CR - Cash Receipt", "JV - Journal Voucher"])
            self.type_combo.setStyleSheet("""
                QComboBox {
                    background-color: #2a2a2a;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    padding: 5px 10px;
                    min-width: 200px;
                }
            """)
            self.type_combo.currentTextChanged.connect(self.on_type_changed)
            type_layout.addWidget(self.type_combo)
            type_layout.addStretch()
            layout.addLayout(type_layout)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # Date
        date_label = QLabel("Date:")
        date_label.setStyleSheet("color: #b0b0b0; font-size: 14px; font-weight: bold;")
        self.date_edit = CompactDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setMinimumHeight(40)
        self.date_edit.setStyleSheet("""
            QDateEdit {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
                min-height: 40px;
            }
        """)
        form_layout.addRow(date_label, self.date_edit)
        
        # CP/CR specific fields (From, To, Amount) - with separate labels for visibility control
        self.from_label = QLabel("From:")
        self.from_label.setStyleSheet("color: #b0b0b0; font-size: 14px; font-weight: bold;")
        self.from_combo = QComboBox()
        self.from_combo.setEditable(True)
        self.from_combo.setMinimumHeight(40)
        self.from_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
                min-height: 40px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #ffffff;
                selection-background-color: #0078d4;
                font-size: 14px;
                padding: 5px;
            }
        """)
        form_layout.addRow(self.from_label, self.from_combo)
        
        self.to_label = QLabel("To:")
        self.to_label.setStyleSheet("color: #b0b0b0; font-size: 14px; font-weight: bold;")
        self.to_combo = QComboBox()
        self.to_combo.setEditable(True)
        self.to_combo.setMinimumHeight(40)
        self.to_combo.setStyleSheet(self.from_combo.styleSheet())
        form_layout.addRow(self.to_label, self.to_combo)
        
        self.amount_label = QLabel("Amount:")
        self.amount_label.setStyleSheet("color: #b0b0b0; font-size: 14px; font-weight: bold;")
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setMaximum(999999999.99)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setMinimumHeight(40)
        self.amount_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
                min-height: 40px;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 25px;
            }
        """)
        form_layout.addRow(self.amount_label, self.amount_spin)
        
        # Description (editable combobox with previous descriptions)
        desc_label = QLabel("Description:")
        desc_label.setStyleSheet("color: #b0b0b0; font-size: 14px; font-weight: bold;")
        self.description_edit = QComboBox()
        self.description_edit.setEditable(True)
        self.description_edit.setMinimumHeight(40)
        self.description_edit.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
                min-height: 40px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #ffffff;
                selection-background-color: #0078d4;
                font-size: 14px;
                padding: 5px;
                max-height: 200px;
            }
        """)
        form_layout.addRow(desc_label, self.description_edit)
        
        layout.addLayout(form_layout)
        
        # Details section (for JV only)
        self.details_label = QLabel("Voucher Details:")
        self.details_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        layout.addWidget(self.details_label)
        
        # Details table (for JV only)
        self.details_table = QTableWidget()
        self.details_table.setColumnCount(3)
        self.details_table.setHorizontalHeaderLabels(["Party/Account", "Debit", "Credit"])
        self.details_table.horizontalHeader().setStretchLastSection(True)
        self.details_table.setColumnWidth(0, 400)
        self.details_table.setColumnWidth(1, 200)
        self.details_table.setColumnWidth(2, 200)
        self.details_table.verticalHeader().setDefaultSectionSize(40)  # Increased row height
        self.details_table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                gridline-color: #3d3d3d;
                border: 1px solid #3d3d3d;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget QComboBox {
                min-height: 30px;
                padding: 5px;
            }
            QTableWidget QDoubleSpinBox {
                min-height: 30px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.details_table)
        
        # Buttons for JV entries
        buttons_layout = QHBoxLayout()
        
        # Add detail button (for JV only)
        self.add_detail_btn = QPushButton("➕ Add Entry")
        self.add_detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.add_detail_btn.clicked.connect(self.add_detail_row)
        buttons_layout.addWidget(self.add_detail_btn)
        
        buttons_layout.addStretch()
        
        # Remove entry button (for JV only)
        self.remove_detail_btn = QPushButton("➖ Remove Entry")
        self.remove_detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        self.remove_detail_btn.clicked.connect(self.remove_detail_row)
        buttons_layout.addWidget(self.remove_detail_btn)
        
        layout.addLayout(buttons_layout)
        
        # Totals (for JV only)
        totals_layout = QHBoxLayout()
        totals_layout.addStretch()
        self.total_debit_label = QLabel("Total Debit: 0.00")
        self.total_debit_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        totals_layout.addWidget(self.total_debit_label)
        totals_layout.addSpacing(20)
        self.total_credit_label = QLabel("Total Credit: 0.00")
        self.total_credit_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        totals_layout.addWidget(self.total_credit_label)
        layout.addLayout(totals_layout)
        
        # Initially hide JV-specific fields
        self.details_label.hide()
        self.details_table.hide()
        self.add_detail_btn.hide()
        self.total_debit_label.hide()
        self.total_credit_label.hide()
        
        # Initially hide CP/CR fields if no type selected
        if not self.voucher_type:
            self.from_label.hide()
            self.from_combo.hide()
            self.to_label.hide()
            self.to_combo.hide()
            self.amount_label.hide()
            self.amount_spin.hide()
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_voucher)
        button_box.rejected.connect(self.reject)
        button_box.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                border: 1px solid #0078d4;
            }
        """)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Trigger initial type change if creating new voucher (CP is default)
        if not self.is_edit_mode and self.type_combo:
            self.on_type_changed(self.type_combo.currentText())
    
    def on_type_changed(self, text):
        """Handle voucher type change"""
        # Safety check: ensure UI elements exist
        if not hasattr(self, 'from_combo') or not hasattr(self, 'to_combo'):
            return
        
        if "CP" in text:
            self.voucher_type = "CP"
            # Show CP/CR fields, hide JV fields
            self.from_combo.setVisible(True)
            self.to_combo.setVisible(True)
            self.amount_spin.setVisible(True)
            # Hide labels for From/To/Amount when showing them
            self.from_label.setVisible(True)
            self.to_label.setVisible(True)
            self.amount_label.setVisible(True)
            self.details_label.hide()
            self.details_table.hide()
            self.add_detail_btn.hide()
            self.total_debit_label.hide()
            self.total_credit_label.hide()
            # Populate From/To for CP
            self.populate_cp_cr_combos()
        elif "CR" in text:
            self.voucher_type = "CR"
            # Show CP/CR fields, hide JV fields
            self.from_combo.setVisible(True)
            self.to_combo.setVisible(True)
            self.amount_spin.setVisible(True)
            self.from_label.setVisible(True)
            self.to_label.setVisible(True)
            self.amount_label.setVisible(True)
            self.details_label.hide()
            self.details_table.hide()
            self.add_detail_btn.hide()
            self.total_debit_label.hide()
            self.total_credit_label.hide()
            # Populate From/To for CR
            self.populate_cp_cr_combos()
        elif "JV" in text:
            self.voucher_type = "JV"
            # Hide CP/CR fields and labels, show JV fields
            self.from_combo.hide()
            self.to_combo.hide()
            self.amount_spin.hide()
            self.from_label.hide()
            self.to_label.hide()
            self.amount_label.hide()
            self.details_label.show()
            self.details_table.show()
            self.add_detail_btn.show()
            self.total_debit_label.show()
            self.total_credit_label.show()
        
        # Clear existing rows
        if hasattr(self, 'details_table'):
            self.details_table.setRowCount(0)
        self.voucher_details = []
        if hasattr(self, 'details_table'):
            self.update_totals()
        if hasattr(self, 'amount_spin'):
            self.amount_spin.setValue(0)
        if hasattr(self, 'from_combo'):
            self.from_combo.setCurrentIndex(0)
        if hasattr(self, 'to_combo'):
            self.to_combo.setCurrentIndex(0)
    
    def load_masters(self):
        """Load liabilities, assets, expenses, and vendors"""
        try:
            # Load liabilities
            response = self.api_client._try_request("GET", "/api/parties")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.liabilities = [p for p in data.get("parties", []) if p.get('is_active', True)]
            
            # Load assets
            response = self.api_client._try_request("GET", "/api/assets")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.assets = data.get("assets", [])
            
            # Load expenses
            response = self.api_client._try_request("GET", "/api/expenses")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.expenses = data.get("expenses", [])
            
            # Load vendors
            response = self.api_client._try_request("GET", "/api/vendors")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.vendors = data.get("vendors", [])
            
            # Load previous descriptions
            self.load_previous_descriptions()
            
            # Populate combos if type is already set
            if self.voucher_type:
                self.populate_cp_cr_combos()
        except Exception as e:
            print(f"Error loading masters: {e}")
    
    def load_previous_descriptions(self):
        """Load previous voucher descriptions for autocomplete"""
        try:
            response = self.api_client._try_request("GET", "/api/vouchers/descriptions")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    descriptions = data.get("descriptions", [])
                    if hasattr(self, 'description_edit'):
                        self.description_edit.clear()
                        # Add "OPENING BALANCE" as the first option (default)
                        self.description_edit.addItem("OPENING BALANCE")
                        # Add other descriptions, but skip "OPENING BALANCE" if it exists to avoid duplicates
                        for desc in descriptions:
                            if desc and desc.upper().strip() != "OPENING BALANCE":
                                self.description_edit.addItem(desc)
        except Exception as e:
            print(f"Error loading previous descriptions: {e}")
    
    def populate_cp_cr_combos(self):
        """Populate From/To combos based on voucher type"""
        if not hasattr(self, 'from_combo') or not hasattr(self, 'to_combo'):
            return
        
        self.from_combo.clear()
        self.to_combo.clear()
        
        # Ensure lists are initialized
        if not hasattr(self, 'expenses'):
            self.expenses = []
        if not hasattr(self, 'vendors'):
            self.vendors = []
        
        if self.voucher_type == "CP":
            # CP: From = Assets (Cash), To = Liabilities + Expenses + Vendors
            self.from_combo.addItem("", None)
            for asset in self.assets:
                if asset.get('is_active', True):
                    self.from_combo.addItem(f"{asset['name']} - assets", ('asset', asset['id']))
            
            self.to_combo.addItem("", None)
            for liability in self.liabilities:
                self.to_combo.addItem(f"{liability['name']} - liabilities", ('liability', liability['id']))
            for expense in self.expenses:
                if expense.get('is_active', True):
                    self.to_combo.addItem(f"{expense['name']} - Expenses", ('expense', expense['id']))
            for vendor in self.vendors:
                if vendor.get('is_active', True):
                    self.to_combo.addItem(f"{vendor['name']} - Vendors", ('vendor', vendor['id']))
        
        elif self.voucher_type == "CR":
            # CR: From = Liabilities + Expenses + Vendors, To = Assets (Cash)
            self.from_combo.addItem("", None)
            for liability in self.liabilities:
                self.from_combo.addItem(f"{liability['name']} - liabilities", ('liability', liability['id']))
            for expense in self.expenses:
                if expense.get('is_active', True):
                    self.from_combo.addItem(f"{expense['name']} - Expenses", ('expense', expense['id']))
            for vendor in self.vendors:
                if vendor.get('is_active', True):
                    self.from_combo.addItem(f"{vendor['name']} - Vendors", ('vendor', vendor['id']))
            
            self.to_combo.addItem("", None)
            for asset in self.assets:
                if asset.get('is_active', True):
                    self.to_combo.addItem(f"{asset['name']} - assets", ('asset', asset['id']))
    
    def load_voucher_data(self):
        """Load existing voucher data for editing"""
        try:
            response = self.api_client._try_request("GET", f"/api/vouchers/{self.voucher_id}")
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    voucher = data.get("voucher", {})
                    self.voucher_type = voucher.get('voucher_type')
                    
                    # Update UI based on type
                    if self.voucher_type in ['CP', 'CR']:
                        self.from_label.setVisible(True)
                        self.from_combo.setVisible(True)
                        self.to_label.setVisible(True)
                        self.to_combo.setVisible(True)
                        self.amount_label.setVisible(True)
                        self.amount_spin.setVisible(True)
                        self.details_label.hide()
                        self.details_table.hide()
                        self.add_detail_btn.hide()
                        self.total_debit_label.hide()
                        self.total_credit_label.hide()
                        self.populate_cp_cr_combos()
                    else:  # JV
                        self.from_label.hide()
                        self.from_combo.hide()
                        self.to_label.hide()
                        self.to_combo.hide()
                        self.amount_label.hide()
                        self.amount_spin.hide()
                        self.details_label.show()
                        self.details_table.show()
                        self.add_detail_btn.show()
                        self.total_debit_label.show()
                        self.total_credit_label.show()
                    
                    # Set date
                    date_str = voucher.get('voucher_date', '')
                    if date_str:
                        try:
                            date = QDate.fromString(date_str[:10], "yyyy-MM-dd")
                            self.date_edit.setDate(date)
                        except:
                            pass
                    
                    # Set description
                    desc = voucher.get('description', '') or ''
                    if desc:
                        # Check if description exists in dropdown, if not add it
                        index = self.description_edit.findText(desc, Qt.MatchExactly)
                        if index >= 0:
                            self.description_edit.setCurrentIndex(index)
                        else:
                            self.description_edit.setEditText(desc)
                    
                    # Load details
                    details = voucher.get('details', [])
                    
                    if self.voucher_type in ['CP', 'CR']:
                        # For CP/CR, populate From/To/Amount from details
                        from_detail = None
                        to_detail = None
                        amount = 0
                        
                        for detail in details:
                            if detail.get('debit_amount'):
                                from_detail = detail
                                amount = detail.get('debit_amount', 0)
                            elif detail.get('credit_amount'):
                                to_detail = detail
                                amount = detail.get('credit_amount', 0)
                        
                        if from_detail:
                            if from_detail.get('asset_id'):
                                for i in range(self.from_combo.count()):
                                    data = self.from_combo.itemData(i)
                                    if data and data[0] == 'asset' and data[1] == from_detail['asset_id']:
                                        self.from_combo.setCurrentIndex(i)
                                        break
                            elif from_detail.get('party_id'):
                                for i in range(self.from_combo.count()):
                                    data = self.from_combo.itemData(i)
                                    if data and data[0] == 'liability' and data[1] == from_detail['party_id']:
                                        self.from_combo.setCurrentIndex(i)
                                        break
                            elif from_detail.get('expense_id'):
                                for i in range(self.from_combo.count()):
                                    data = self.from_combo.itemData(i)
                                    if data and data[0] == 'expense' and data[1] == from_detail['expense_id']:
                                        self.from_combo.setCurrentIndex(i)
                                        break
                            elif from_detail.get('vendor_id'):
                                for i in range(self.from_combo.count()):
                                    data = self.from_combo.itemData(i)
                                    if data and data[0] == 'vendor' and data[1] == from_detail['vendor_id']:
                                        self.from_combo.setCurrentIndex(i)
                                        break
                        
                        if to_detail:
                            if to_detail.get('asset_id'):
                                for i in range(self.to_combo.count()):
                                    data = self.to_combo.itemData(i)
                                    if data and data[0] == 'asset' and data[1] == to_detail['asset_id']:
                                        self.to_combo.setCurrentIndex(i)
                                        break
                            elif to_detail.get('party_id'):
                                for i in range(self.to_combo.count()):
                                    data = self.to_combo.itemData(i)
                                    if data and data[0] == 'liability' and data[1] == to_detail['party_id']:
                                        self.to_combo.setCurrentIndex(i)
                                        break
                            elif to_detail.get('expense_id'):
                                for i in range(self.to_combo.count()):
                                    data = self.to_combo.itemData(i)
                                    if data and data[0] == 'expense' and data[1] == to_detail['expense_id']:
                                        self.to_combo.setCurrentIndex(i)
                                        break
                            elif to_detail.get('vendor_id'):
                                for i in range(self.to_combo.count()):
                                    data = self.to_combo.itemData(i)
                                    if data and data[0] == 'vendor' and data[1] == to_detail['vendor_id']:
                                        self.to_combo.setCurrentIndex(i)
                                        break
                        
                        self.amount_spin.setValue(amount)
                    else:
                        # For JV, load into table
                        for detail in details:
                            self.add_detail_row_from_data(detail)
                        self.update_totals()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load voucher: {str(e)}")
    
    def add_detail_row(self):
        """Add a new detail row"""
        row = self.details_table.rowCount()
        self.details_table.insertRow(row)
        
        # Party/Account combo
        party_combo = QComboBox()
        party_combo.setEditable(True)
        party_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        
        # Populate based on voucher type
        if self.voucher_type == "CP":
            # From: Assets (Cash), To: Liabilities
            party_combo.addItem("", None)  # Empty option
            for asset in self.assets:
                if asset.get('is_active', True):
                    party_combo.addItem(f"{asset['name']} - assets", ('asset', asset['id']))
            for liability in self.liabilities:
                party_combo.addItem(f"{liability['name']} - liabilities", ('liability', liability['id']))
        elif self.voucher_type == "CR":
            # From: Liabilities, To: Assets (Cash)
            party_combo.addItem("", None)
            for liability in self.liabilities:
                party_combo.addItem(f"{liability['name']} - liabilities", ('liability', liability['id']))
            for asset in self.assets:
                if asset.get('is_active', True):
                    party_combo.addItem(f"{asset['name']} - assets", ('asset', asset['id']))
        else:  # JV
            # Assets, liabilities, expenses, and vendors
            party_combo.addItem("", None)
            for asset in self.assets:
                if asset.get('is_active', True):
                    party_combo.addItem(f"{asset['name']} - assets", ('asset', asset['id']))
            for liability in self.liabilities:
                party_combo.addItem(f"{liability['name']} - liabilities", ('liability', liability['id']))
            for expense in self.expenses:
                if expense.get('is_active', True):
                    party_combo.addItem(f"{expense['name']} - Expenses", ('expense', expense['id']))
            for vendor in self.vendors:
                if vendor.get('is_active', True):
                    party_combo.addItem(f"{vendor['name']} - Vendors", ('vendor', vendor['id']))
        
        self.details_table.setCellWidget(row, 0, party_combo)
        
        # Debit amount
        debit_spin = QDoubleSpinBox()
        debit_spin.setMaximum(999999999.99)
        debit_spin.setDecimals(2)
        debit_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        debit_spin.valueChanged.connect(self.update_totals)
        self.details_table.setCellWidget(row, 1, debit_spin)
        
        # Credit amount
        credit_spin = QDoubleSpinBox()
        credit_spin.setMaximum(999999999.99)
        credit_spin.setDecimals(2)
        credit_spin.setStyleSheet(debit_spin.styleSheet())
        credit_spin.valueChanged.connect(self.update_totals)
        self.details_table.setCellWidget(row, 2, credit_spin)
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        delete_btn.clicked.connect(lambda checked, r=row: self.delete_detail_row(r))
        self.details_table.setCellWidget(row, 3, delete_btn)
        
        # Connect debit/credit mutual exclusivity
        def on_debit_changed(value):
            if value > 0:
                credit_spin.setValue(0)
        
        def on_credit_changed(value):
            if value > 0:
                debit_spin.setValue(0)
        
        debit_spin.valueChanged.connect(on_debit_changed)
        credit_spin.valueChanged.connect(on_credit_changed)
    
    def remove_detail_row(self):
        """Remove a detail row - removes selected row or last row if none selected"""
        if self.details_table.rowCount() == 0:
            return
        
        # Get selected row
        selected_rows = self.details_table.selectionModel().selectedRows()
        
        if selected_rows:
            # Remove selected row
            row = selected_rows[0].row()
            self.details_table.removeRow(row)
        else:
            # Remove last row
            last_row = self.details_table.rowCount() - 1
            self.details_table.removeRow(last_row)
        
        self.update_totals()
    
    def add_detail_row_from_data(self, detail_data):
        """Add detail row from existing data"""
        row = self.details_table.rowCount()
        self.details_table.insertRow(row)
        
        # Party/Account combo
        party_combo = QComboBox()
        party_combo.setEditable(True)
        party_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        
        # Populate
        party_combo.addItem("", None)
        for asset in self.assets:
            if asset.get('is_active', True):
                party_combo.addItem(f"{asset['name']} - assets", ('asset', asset['id']))
        for liability in self.liabilities:
            party_combo.addItem(f"{liability['name']} - liabilities", ('liability', liability['id']))
        for expense in self.expenses:
            if expense.get('is_active', True):
                party_combo.addItem(f"{expense['name']} - Expenses", ('expense', expense['id']))
        for vendor in self.vendors:
            if vendor.get('is_active', True):
                party_combo.addItem(f"{vendor['name']} - Vendors", ('vendor', vendor['id']))
        
        # Set selected value
        if detail_data.get('asset_id'):
            for i in range(party_combo.count()):
                data = party_combo.itemData(i)
                if data and data[0] == 'asset' and data[1] == detail_data['asset_id']:
                    party_combo.setCurrentIndex(i)
                    break
        elif detail_data.get('party_id'):
            for i in range(party_combo.count()):
                data = party_combo.itemData(i)
                if data and data[0] == 'liability' and data[1] == detail_data['party_id']:
                    party_combo.setCurrentIndex(i)
                    break
        elif detail_data.get('expense_id'):
            for i in range(party_combo.count()):
                data = party_combo.itemData(i)
                if data and data[0] == 'expense' and data[1] == detail_data['expense_id']:
                    party_combo.setCurrentIndex(i)
                    break
        elif detail_data.get('vendor_id'):
            for i in range(party_combo.count()):
                data = party_combo.itemData(i)
                if data and data[0] == 'vendor' and data[1] == detail_data['vendor_id']:
                    party_combo.setCurrentIndex(i)
                    break
        
        self.details_table.setCellWidget(row, 0, party_combo)
        
        # Debit amount
        debit_spin = QDoubleSpinBox()
        debit_spin.setMaximum(999999999.99)
        debit_spin.setDecimals(2)
        debit_spin.setValue(detail_data.get('debit_amount') or 0)
        debit_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                min-height: 30px;
            }
        """)
        debit_spin.valueChanged.connect(self.update_totals)
        self.details_table.setCellWidget(row, 1, debit_spin)
        
        # Credit amount
        credit_spin = QDoubleSpinBox()
        credit_spin.setMaximum(999999999.99)
        credit_spin.setDecimals(2)
        credit_spin.setValue(detail_data.get('credit_amount') or 0)
        credit_spin.setStyleSheet(debit_spin.styleSheet())
        credit_spin.valueChanged.connect(self.update_totals)
        self.details_table.setCellWidget(row, 2, credit_spin)
        
        # Connect mutual exclusivity
        def on_debit_changed(value):
            if value > 0:
                credit_spin.setValue(0)
        
        def on_credit_changed(value):
            if value > 0:
                debit_spin.setValue(0)
        
        debit_spin.valueChanged.connect(on_debit_changed)
        credit_spin.valueChanged.connect(on_credit_changed)
    
    def remove_detail_row(self):
        """Remove a detail row - removes selected row or last row if none selected"""
        if self.details_table.rowCount() == 0:
            return
        
        # Get selected row
        selected_rows = self.details_table.selectionModel().selectedRows()
        
        if selected_rows:
            # Remove selected row
            row = selected_rows[0].row()
            self.details_table.removeRow(row)
        else:
            # Remove last row
            last_row = self.details_table.rowCount() - 1
            self.details_table.removeRow(last_row)
        
        self.update_totals()
    
    def update_totals(self):
        """Update debit and credit totals"""
        total_debit = 0.0
        total_credit = 0.0
        
        for row in range(self.details_table.rowCount()):
            debit_widget = self.details_table.cellWidget(row, 1)
            credit_widget = self.details_table.cellWidget(row, 2)
            
            if debit_widget:
                total_debit += debit_widget.value()
            if credit_widget:
                total_credit += credit_widget.value()
        
        self.total_debit_label.setText(f"Total Debit: {total_debit:,.2f}")
        self.total_credit_label.setText(f"Total Credit: {total_credit:,.2f}")
        
        # Highlight if not balanced
        if abs(total_debit - total_credit) > 0.01:
            self.total_debit_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
            self.total_credit_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        else:
            self.total_debit_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.total_credit_label.setStyleSheet("color: #4caf50; font-weight: bold;")
    
    def save_voucher(self):
        """Save voucher to database"""
        if not self.voucher_type:
            QMessageBox.warning(self, "Validation", "Please select a voucher type")
            return
        
        details = []
        
        if self.voucher_type in ['CP', 'CR']:
            # CP/CR: Simple From/To/Amount format
            from_data = self.from_combo.currentData()
            to_data = self.to_combo.currentData()
            amount = self.amount_spin.value()
            
            if not from_data:
                QMessageBox.warning(self, "Validation", "Please select 'From' party/account")
                return
            
            if not to_data:
                QMessageBox.warning(self, "Validation", "Please select 'To' party/account")
                return
            
            if amount <= 0:
                QMessageBox.warning(self, "Validation", "Please enter an amount greater than 0")
                return
            
            # Create two detail entries: From (Debit) and To (Credit)
            from_detail = {}
            if from_data[0] == 'asset':
                from_detail['asset_id'] = from_data[1]
            elif from_data[0] == 'liability':
                from_detail['party_id'] = from_data[1]
            elif from_data[0] == 'expense':
                from_detail['expense_id'] = from_data[1]
            elif from_data[0] == 'vendor':
                from_detail['vendor_id'] = from_data[1]
            from_detail['debit_amount'] = amount
            from_detail['credit_amount'] = None
            details.append(from_detail)
            
            to_detail = {}
            if to_data[0] == 'asset':
                to_detail['asset_id'] = to_data[1]
            elif to_data[0] == 'liability':
                to_detail['party_id'] = to_data[1]
            elif to_data[0] == 'expense':
                to_detail['expense_id'] = to_data[1]
            elif to_data[0] == 'vendor':
                to_detail['vendor_id'] = to_data[1]
            to_detail['debit_amount'] = None
            to_detail['credit_amount'] = amount
            details.append(to_detail)
        
        else:
            # JV: Multiple entries from table
            if self.details_table.rowCount() == 0:
                QMessageBox.warning(self, "Validation", "Please add at least one voucher detail")
                return
            
            asset_count = 0
            
            for row in range(self.details_table.rowCount()):
                party_combo = self.details_table.cellWidget(row, 0)
                debit_widget = self.details_table.cellWidget(row, 1)
                credit_widget = self.details_table.cellWidget(row, 2)
                
                if not party_combo:
                    continue
                
                party_data = party_combo.currentData()
                if not party_data:
                    QMessageBox.warning(self, "Validation", f"Please select a party/account for row {row + 1}")
                    return
                
                debit = debit_widget.value() if debit_widget else 0
                credit = credit_widget.value() if credit_widget else 0
                
                if debit == 0 and credit == 0:
                    QMessageBox.warning(self, "Validation", f"Please enter either debit or credit amount for row {row + 1}")
                    return
                
                if debit > 0 and credit > 0:
                    QMessageBox.warning(self, "Validation", f"Row {row + 1} cannot have both debit and credit")
                    return
                
                detail_item = {}
                if party_data[0] == 'asset':
                    detail_item['asset_id'] = party_data[1]
                    asset_count += 1
                elif party_data[0] == 'liability':
                    detail_item['party_id'] = party_data[1]
                elif party_data[0] == 'expense':
                    detail_item['expense_id'] = party_data[1]
                elif party_data[0] == 'vendor':
                    detail_item['vendor_id'] = party_data[1]
                else:
                    # Fallback to party_id for unknown types
                    detail_item['party_id'] = party_data[1]
                
                if debit > 0:
                    detail_item['debit_amount'] = debit
                    detail_item['credit_amount'] = None
                else:
                    detail_item['debit_amount'] = None
                    detail_item['credit_amount'] = credit
                
                details.append(detail_item)
            
            # Validate totals for JV
            total_debit = sum(d.get('debit_amount') or 0 for d in details)
            total_credit = sum(d.get('credit_amount') or 0 for d in details)
            
            if abs(total_debit - total_credit) > 0.01:
                QMessageBox.warning(self, "Validation", f"Debit total ({total_debit:,.2f}) must equal credit total ({total_credit:,.2f})")
                return
        
        # Validate description - check if user typed their own opening balance
        description = self.description_edit.currentText().strip()
        description_upper = description.upper()
        
        # Check if description contains "opening balance" but is not exactly "OPENING BALANCE"
        if "opening balance" in description_upper or "opening bal" in description_upper:
            if description_upper != "OPENING BALANCE":
                QMessageBox.warning(
                    self, 
                    "Invalid Description", 
                    "Please select 'OPENING BALANCE' from the dropdown for opening balance entries.\n\n"
                    "Do not type your own opening balance description. Use the dropdown option."
                )
                # Try to set it to OPENING BALANCE
                index = self.description_edit.findText("OPENING BALANCE", Qt.MatchExactly)
                if index >= 0:
                    self.description_edit.setCurrentIndex(index)
                else:
                    # If not found, add it and set it
                    self.description_edit.insertItem(0, "OPENING BALANCE")
                    self.description_edit.setCurrentIndex(0)
                return
        
        # Check for duplicate opening balance entries if description is "OPENING BALANCE"
        if description_upper == "OPENING BALANCE":
            # Get all party/account names from voucher details
            party_names_to_check = []
            
            for detail in details:
                party_name = None
                if detail.get('party_id'):
                    # Find party name
                    for liability in self.liabilities:
                        if liability.get('id') == detail['party_id']:
                            party_name = liability.get('name')
                            break
                elif detail.get('asset_id'):
                    # Find asset name
                    for asset in self.assets:
                        if asset.get('id') == detail['asset_id']:
                            party_name = asset.get('name')
                            break
                elif detail.get('expense_id'):
                    # Find expense name
                    for expense in self.expenses:
                        if expense.get('id') == detail['expense_id']:
                            party_name = expense.get('name')
                            break
                elif detail.get('vendor_id'):
                    # Find vendor name
                    for vendor in self.vendors:
                        if vendor.get('id') == detail['vendor_id']:
                            party_name = vendor.get('name')
                            break
                
                if party_name:
                    party_names_to_check.append(party_name)
            
            # Check if any of these parties already have an opening balance entry
            parties_with_opening_balance = []
            
            try:
                # Get all financial ledgers
                response = self.api_client._try_request("GET", "/api/financial-ledgers")
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        ledgers = data.get("ledgers", [])
                        
                        # Get current voucher number if editing (to exclude it from check)
                        current_voucher_no = None
                        if self.is_edit_mode:
                            try:
                                voucher_response = self.api_client._try_request("GET", f"/api/vouchers/{self.voucher_id}")
                                if voucher_response and voucher_response.status_code == 200:
                                    voucher_data = voucher_response.json()
                                    if voucher_data.get("success"):
                                        current_voucher = voucher_data.get("voucher", {})
                                        current_voucher_no = current_voucher.get('voucher_no')
                            except:
                                pass
                        
                        # Find ledgers for the parties in this voucher
                        for party_name in party_names_to_check:
                            # Find ledger for this party
                            ledger_id = None
                            for ledger in ledgers:
                                if ledger.get('name') == party_name:
                                    ledger_id = ledger.get('id')
                                    break
                            
                            if ledger_id:
                                # Check if this ledger already has an opening balance entry
                                entries_response = self.api_client._try_request("GET", f"/api/financial-ledgers/{ledger_id}/entries")
                                if entries_response and entries_response.status_code == 200:
                                    entries_data = entries_response.json()
                                    if entries_data.get("success"):
                                        entries = entries_data.get("entries", [])
                                        # Check if any entry has "OPENING BALANCE" description
                                        for entry in entries:
                                            entry_desc = entry.get('description', '').strip().upper()
                                            # Skip current voucher if editing
                                            if current_voucher_no and entry.get('voucher_number') == current_voucher_no:
                                                continue
                                            
                                            if entry_desc == "OPENING BALANCE":
                                                parties_with_opening_balance.append(party_name)
                                                break
                
                if parties_with_opening_balance:
                    party_list = ", ".join(set(parties_with_opening_balance))  # Remove duplicates
                    QMessageBox.warning(
                        self,
                        "Duplicate Opening Balance",
                        f"The following party/account already has an opening balance entry:\n\n{party_list}\n\n"
                        "Each party/account can only have one opening balance entry. "
                        "Please use a different description or remove the existing opening balance entry first."
                    )
                    return
            except Exception as e:
                print(f"Error checking for duplicate opening balance: {e}")
                import traceback
                traceback.print_exc()
                # Continue with save if check fails (don't block user)
        
        # Prepare request
        request_data = {
            "voucher_type": self.voucher_type,
            "voucher_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "description": description,
            "details": details
        }
        
        try:
            if self.is_edit_mode:
                request_data['voucher_id'] = self.voucher_id
                response = self.api_client._try_request_with_retry("PUT", f"/api/vouchers/{self.voucher_id}", json=request_data)
                success_msg = "Voucher updated successfully"
            else:
                response = self.api_client._try_request_with_retry("POST", "/api/vouchers", json=request_data)
                success_msg = "Voucher created successfully"
            
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    QMessageBox.information(self, "Success", success_msg)
                    self.accept()
                else:
                    QMessageBox.warning(self, "Error", data.get("message", "Failed to save voucher"))
            elif response is None:
                # Connection failed after all retries
                QMessageBox.warning(
                    self, "Connection Error",
                    "Unable to connect to the server after multiple attempts.\n\n"
                    "Please check your network connection and try again.\n"
                    "Your data has been preserved in the form."
                )
            else:
                error_detail = "Failed to save voucher"
                try:
                    if response:
                        error_data = response.json() if response.content else {}
                        error_detail = error_data.get("detail", error_detail)
                except:
                    pass
                QMessageBox.warning(self, "Error", error_detail)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving voucher: {str(e)}")
