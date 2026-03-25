"""Invoice Module UI"""

import sys
import traceback
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QLineEdit, QFormLayout,
    QDialogButtonBox, QMessageBox, QComboBox, QDoubleSpinBox, QDateEdit,
    QAbstractItemView, QListWidget, QListWidgetItem, QCheckBox, QSpinBox,
    QCompleter
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import requests
import os
import tempfile
import webbrowser
import base64
from common.config import CLIENT_FALLBACK_SERVER
from client.api_client import APIClient


# ==================== DOCUMENT LOADER ====================

class InvoiceLoader(QThread):
    """Thread for loading invoices asynchronously"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._stop_requested = False
    
    def stop(self):
        """Request thread to stop"""
        self._stop_requested = True
    
    def run(self):
        try:
            print("[InvoiceLoader] Starting invoice load request...")
            api_client = APIClient()
            print(f"[InvoiceLoader] APIClient mode: {'HOST' if api_client.is_host_mode else 'CLIENT'}")
            print(f"[InvoiceLoader] Primary server: {api_client.primary_server}")
            print(f"[InvoiceLoader] Fallback server: {api_client.fallback_server}")
            print(f"[InvoiceLoader] Timeout: {api_client.timeout}s (remote), {api_client.localhost_timeout}s (localhost)")
            response = api_client._try_request("GET", "/api/invoice")
            print(f"[InvoiceLoader] Response received: {response is not None}")
            if response:
                print(f"[InvoiceLoader] Response status: {response.status_code}")
                print(f"[InvoiceLoader] Current server: {api_client.current_server}")
            if self._stop_requested:
                print("[InvoiceLoader] Stop requested, aborting...")
                return
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    if not self._stop_requested:
                        invoices = data.get("invoices", [])
                        print(f"[InvoiceLoader] Successfully loaded {len(invoices)} invoices")
                        self.finished.emit(invoices)
                else:
                    error_msg = data.get("message", "Failed to load invoices")
                    print(f"[InvoiceLoader] ERROR - Server returned unsuccessful: {error_msg}")
                    print(f"[InvoiceLoader] Full response: {data}")
                    if not self._stop_requested:
                        self.error.emit(error_msg)
            else:
                status = response.status_code if response else "connection_error"
                error_msg = f"Server error: {status}"
                print(f"[InvoiceLoader] ERROR - {error_msg}")
                if response:
                    print(f"[InvoiceLoader] Response status: {response.status_code}")
                    try:
                        print(f"[InvoiceLoader] Response body: {response.text[:500]}")
                    except:
                        pass
                else:
                    print("[InvoiceLoader] No response received - connection failed")
                if not self._stop_requested:
                    self.error.emit(error_msg)
        except Exception as e:
            error_msg = str(e)
            print(f"[InvoiceLoader] EXCEPTION - {type(e).__name__}: {error_msg}")
            print("[InvoiceLoader] Full traceback:")
            traceback.print_exc(file=sys.stdout)
            if not self._stop_requested:
                self.error.emit(error_msg)


# ==================== INVOICE MODULE ====================

class InvoiceModule(QWidget):
    """Invoice Management Module"""
    
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data
        self.ws_bus = (user_data or {}).get("ws_bus")
        self.server_available = True
        self.all_invoices = []
        self.api_client = APIClient()
        # Set username on API client for edited_by tracking
        if user_data and user_data.get('username'):
            self.api_client.set_username(user_data.get('username'))
        self._data_loaded = False  # Track if data has been loaded
        self.loader = None  # Track loader thread for cleanup
        self.init_ui()
        if self.ws_bus:
            try:
                self.ws_bus.message.connect(self.on_realtime_message)
            except Exception:
                pass
        # Don't load data immediately - wait until module is shown
    
    def closeEvent(self, event):
        """Clean up threads before closing"""
        if self.loader and self.loader.isRunning():
            self.loader.quit()
            self.loader.wait(1000)  # Wait up to 1 second for thread to finish
            if self.loader.isRunning():
                self.loader.terminate()
                self.loader.wait(500)
        event.accept()
    
    def load_data_if_needed(self):
        """Load data if not already loaded (called explicitly when module is shown)"""
        if not self._data_loaded:
            self._data_loaded = True
            self.load_invoices_async()
    
    def showEvent(self, event):
        """Handle show event (but don't load here - use load_data_if_needed instead)"""
        super().showEvent(event)

    def on_realtime_message(self, message: dict):
        """Apply server-pushed CRUD updates (so client UIs update instantly)."""
        if not isinstance(message, dict):
            return
        if message.get("type") != "entity_change":
            return
        if message.get("entity") != "invoice":
            return

        action = message.get("action")
        data = message.get("data") or {}
        if action in ("created", "updated"):
            if isinstance(data, dict) and data.get("id"):
                self._upsert_invoice(data, prefer_top=(action == "created"))
        elif action == "deleted":
            inv_id = data.get("id") if isinstance(data, dict) else None
            if inv_id:
                self._remove_invoice_by_id(inv_id)

    def _upsert_invoice(self, invoice: dict, prefer_top: bool = False):
        # Safety check: ensure widget still exists
        if not hasattr(self, 'table') or self.table is None:
            return
        try:
            _ = self.table.objectName()
        except RuntimeError:
            # Widget was deleted, ignore update
            return
        
        if not hasattr(self, "all_invoices") or self.all_invoices is None:
            self.all_invoices = []
        inv_id = invoice.get("id")
        if not inv_id:
            return
        existing_idx = next((i for i, inv in enumerate(self.all_invoices) if inv.get("id") == inv_id), None)
        if existing_idx is None:
            if prefer_top:
                self.all_invoices.insert(0, invoice)
            else:
                self.all_invoices.append(invoice)
        else:
            self.all_invoices[existing_idx] = invoice
        self.populate_table(self.all_invoices)

    def _remove_invoice_by_id(self, invoice_id: int):
        # Safety check: ensure widget still exists
        if not hasattr(self, 'table') or self.table is None:
            return
        try:
            _ = self.table.objectName()
        except RuntimeError:
            # Widget was deleted, ignore update
            return
        
        if not hasattr(self, "all_invoices") or not self.all_invoices:
            return
        self.all_invoices = [inv for inv in self.all_invoices if inv.get("id") != invoice_id]
        self.populate_table(self.all_invoices)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("🧾 Invoices")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)
        header.addStretch()
        
        # Buttons
        self.add_btn = QPushButton("➕ Add Invoice")
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
        self.add_btn.clicked.connect(self.add_invoice)
        header.addWidget(self.add_btn)
        
        self.print_btn = QPushButton("🖨️ Print")
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.print_btn.clicked.connect(self.print_invoices)
        header.addWidget(self.print_btn)
        
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
        self.refresh_btn.clicked.connect(self.load_invoices_async)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "INVOICE #", "MS PARTY", "NO OF ITEMS", "DISCOUNT", "TOTAL AMOUNT", "DATE"
        ])
        # Set column widths to fill remaining space
        self.table.setColumnWidth(0, 180)  # INVOICE #
        self.table.setColumnWidth(1, 250)  # MS PARTY
        self.table.setColumnWidth(2, 150)  # NO OF ITEMS
        self.table.setColumnWidth(3, 150)  # DISCOUNT
        self.table.setColumnWidth(4, 180)  # TOTAL AMOUNT
        self.table.setColumnWidth(5, 150)  # DATE
        self.table.horizontalHeader().setStretchLastSection(True)  # Stretch last column
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                gridline-color: #3d3d3d;
                color: #ffffff;
                alternate-background-color: #252525;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                padding: 12px 15px;
                color: #ffffff;
                font-weight: bold;
                border: none;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #666666;
            }
        """)
        self.edit_btn.clicked.connect(self.edit_selected_invoice)
        self.edit_btn.setEnabled(False)
        action_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d83b01;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #a02d01;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #666666;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_selected_invoice)
        self.delete_btn.setEnabled(False)
        action_layout.addWidget(self.delete_btn)
        
        layout.addLayout(action_layout)
        self.setLayout(layout)
    
    def on_selection_changed(self):
        """Enable/disable edit and delete buttons based on selection"""
        selected_rows = self.table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def load_invoices_async(self):
        """Load invoices asynchronously"""
        # Clean up any existing loader thread
        if self.loader and self.loader.isRunning():
            self.loader.stop()
            self.loader.quit()
            self.loader.wait(500)
        
        # Mark that we've attempted initial load
        if not hasattr(self, '_initial_load_complete'):
            self._initial_load_complete = False
        self.loader = InvoiceLoader()
        self.loader.finished.connect(self._on_load_finished)
        self.loader.error.connect(self.on_load_error)
        self.loader.start()
    
    def _on_load_finished(self, invoices):
        """Handle successful load"""
        self._initial_load_complete = True
        self.server_available = True
        self.populate_table(invoices)
    
    def populate_table(self, invoices):
        """Populate table with invoices"""
        # Safety check: ensure widget still exists
        if not hasattr(self, 'table') or self.table is None:
            return
        try:
            _ = self.table.objectName()
        except RuntimeError:
            # Widget was deleted
            return
        
        self.all_invoices = invoices
        try:
            self.table.setRowCount(len(invoices))
            
            for row, invoice in enumerate(invoices):
                self.table.setItem(row, 0, QTableWidgetItem(invoice.get('invoice_number', '')))
                self.table.setItem(row, 1, QTableWidgetItem(invoice.get('ms_party_name', '')))
                self.table.setItem(row, 2, QTableWidgetItem(str(invoice.get('number_of_items', 0))))
                discount = invoice.get('discount_amount', 0)
                discount_str = f"{discount:.2f}"
                self.table.setItem(row, 3, QTableWidgetItem(discount_str))
                total = invoice.get('total_amount', 0)
                total_str = f"{total:.2f}"
                self.table.setItem(row, 4, QTableWidgetItem(total_str))
                date_str = invoice.get('invoice_date', '')
                if date_str:
                    date_str = date_str[:10]  # Just the date part
                self.table.setItem(row, 5, QTableWidgetItem(date_str))
                self.table.item(row, 0).setData(Qt.UserRole, invoice.get('id'))
        except RuntimeError:
            # Widget was deleted during operation
            pass
    
    def on_load_error(self, error):
        """Handle load error - show non-blocking status message instead of dialog"""
        print(f"[InvoiceModule] on_load_error called with error: {error}")
        print(f"[InvoiceModule] Error type: {type(error).__name__}")
        self.server_available = False
        
        # Only show blocking dialog if user explicitly clicked refresh
        # For initial load, just show empty table (less intrusive)
        if not hasattr(self, '_initial_load_complete'):
            # Initial load failed - silently fail, show empty table
            print("[InvoiceModule] Initial load failed - showing empty table (no dialog)")
            self._initial_load_complete = True
            try:
                self.populate_table([])  # Show empty table
            except Exception as e:
                print(f"[InvoiceModule] ERROR in populate_table during error handling: {e}")
                traceback.print_exc(file=sys.stdout)
            # Optionally show a status message in the UI (non-blocking)
            if hasattr(self, 'table') and self.table:
                try:
                    # Add a status row or message
                    pass  # Empty table is sufficient
                except RuntimeError:
                    pass
        else:
            # User explicitly clicked refresh - show error dialog
            print("[InvoiceModule] User-initiated refresh failed - showing error dialog")
            QMessageBox.warning(self, "Error", f"Failed to load invoices: {error}")
    
    def edit_selected_invoice(self):
        """Edit selected invoice"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select an invoice to edit")
            return
        
        row = selected_rows[0].row()
        invoice_id = self.table.item(row, 0).data(Qt.UserRole)
        
        if not invoice_id:
            QMessageBox.warning(self, "Error", "Could not find invoice ID")
            return
        
        # Load invoice data and open edit dialog
        dialog = InvoiceDialog(self, user_data=self.user_data, invoice_id=invoice_id)
        if dialog.exec_() == QDialog.Accepted:
            saved = getattr(dialog, "saved_invoice", None)
            if isinstance(saved, dict) and saved.get("id"):
                self._upsert_invoice(saved, prefer_top=False)
            else:
                self.load_invoices_async()
    
    def delete_selected_invoice(self):
        """Delete selected invoice"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select an invoice to delete")
            return
        
        row = selected_rows[0].row()
        invoice_id = self.table.item(row, 0).data(Qt.UserRole)
        invoice_number = self.table.item(row, 0).text()
        
        if not invoice_id:
            QMessageBox.warning(self, "Error", "Could not find invoice ID")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            f"Are you sure you want to delete invoice {invoice_number}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                response = self.api_client._try_request_with_retry("DELETE", f"/api/invoice/{invoice_id}")
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        QMessageBox.information(self, "Success", "Invoice deleted successfully")
                        self._remove_invoice_by_id(invoice_id)
                    else:
                        QMessageBox.warning(self, "Error", data.get("message", "Failed to delete invoice"))
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete invoice")
            except Exception as e:
                error_msg = str(e)
                print(f"[InvoiceModule] EXCEPTION in delete_selected_invoice: {type(e).__name__}: {error_msg}")
                print("[InvoiceModule] Full traceback:")
                traceback.print_exc(file=sys.stdout)
                QMessageBox.critical(self, "Error", f"Failed to delete invoice: {error_msg}")
    
    def add_invoice(self):
        if not self.server_available:
            QMessageBox.warning(self, "Server Offline", "Server is not available.")
            return
        
        # Show search dialog first to select MS Party
        search_dialog = MSPartySearchDialog(self)
        if search_dialog.exec_() == QDialog.Accepted:
            selected_party = search_dialog.selected_party
            party_rates = search_dialog.party_rates  # Get party rates from search dialog
            if selected_party:
                # Create invoice dialog with pre-selected party and rates
                dialog = InvoiceDialog(self, user_data=self.user_data, preselected_party=selected_party, party_rates=party_rates)
                if dialog.exec_() == QDialog.Accepted:
                    saved = getattr(dialog, "saved_invoice", None)
                    if isinstance(saved, dict) and saved.get("id"):
                        self._upsert_invoice(saved, prefer_top=True)
                    else:
                        self.load_invoices_async()
            else:
                QMessageBox.warning(self, "Validation", "Please select an MS Party")
    
    def print_invoices(self):
        """Show print dialog and print selected invoices"""
        if not self.server_available:
            QMessageBox.warning(self, "Server Offline", "Server is not available.")
            return
        
        # Get selected rows
        selected_rows = self.table.selectionModel().selectedRows()
        selected_indices = set([row.row() for row in selected_rows])
        
        # Show print dialog
        dialog = PrintInvoiceDialog(self, selected_indices, self.all_invoices)
        if dialog.exec_() == QDialog.Accepted:
            selected_ids = dialog.get_selected_ids()
            if selected_ids:
                self.generate_and_print_html(selected_ids)
            else:
                QMessageBox.warning(self, "No Selection", "Please select at least one invoice to print")
    
    def generate_and_print_html(self, invoice_ids):
        """Generate HTML for printing and open in Chrome"""
        try:
            # Fetch all invoice documents
            invoices = []
            for invoice_id in invoice_ids:
                try:
                    response = requests.get(
                        f"{CLIENT_FALLBACK_SERVER}/api/invoice/{invoice_id}",
                        timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            invoices.append(data.get("invoice"))
                except Exception as e:
                    error_msg = str(e)
                    print(f"[InvoiceModule] ERROR loading invoice {invoice_id}: {type(e).__name__}: {error_msg}")
                    traceback.print_exc(file=sys.stdout)
                    QMessageBox.warning(self, "Error", f"Failed to load invoice {invoice_id}: {error_msg}")
            
            if not invoices:
                QMessageBox.warning(self, "Error", "No invoices to print")
                return
            
            # Generate HTML
            html_content = self.generate_invoice_print_html(invoices)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(html_content)
                temp_file_path = temp_file.name
            
            # Open in Chrome
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
            
            chrome_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
            
            if chrome_path:
                import subprocess
                # Open in new tab instead of new window
                subprocess.Popen([chrome_path, '--new-tab', 'file://' + temp_file_path.replace('\\', '/')])
            else:
                # Fallback to default browser
                webbrowser.open('file://' + temp_file_path)
                QMessageBox.information(
                    self, "Print", 
                    "Print dialog opened. Please use Ctrl+P or File > Print to print the document."
                )
                
        except Exception as e:
            error_msg = str(e)
            print(f"[InvoiceModule] EXCEPTION in generate_and_print_html: {type(e).__name__}: {error_msg}")
            print("[InvoiceModule] Full traceback:")
            traceback.print_exc(file=sys.stdout)
            QMessageBox.critical(self, "Error", f"Failed to generate print document: {error_msg}")
    
    def find_logo_file(self):
        """Find logo file in common locations"""
        logo_names = ['logo.png', 'logo.jpg', 'logo.jpeg', 'Logo.png', 'Logo.jpg', 'Logo.jpeg']
        search_paths = [
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
    
    def generate_invoice_print_html(self, invoices):
        """Generate print-ready HTML for invoice documents"""
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
    <title>Print Invoice Documents</title>
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
        
        .form:last-child {
            margin-bottom: 0;
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
        
        .logo img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            background: transparent;
        }
        
        .owner-info {
            text-align: center;
            font-size: 12px;
            margin-bottom: 2mm;
            color: #333333;
        }
        
        .subtitle {
            text-align: center;
            font-size: 18px;
            font-weight: bold;
            margin: 5mm 0;
            text-decoration: underline;
            color: #cc0000;
        }
        
        .meta-info {
            margin-bottom: 5mm;
            background: #e8f4f8;
            padding: 5mm;
            border-radius: 3px;
        }
        
        .meta-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 2mm;
            font-size: 11px;
            color: #1a1a1a;
        }
        
        .meta-label {
            font-weight: bold;
            display: inline-block;
            min-width: 80px;
            color: #0066cc;
        }
        
        .meta-value {
            border-bottom: 1px solid #333;
            display: inline-block;
            min-width: 120px;
            color: #1a1a1a;
        }
        
        .outward-section {
            margin-top: 5mm;
            margin-bottom: 5mm;
        }
        
        .outward-header {
            background: #0066cc;
            color: white;
            padding: 3mm;
            font-weight: bold;
            font-size: 13px;
            border-radius: 3px 3px 0 0;
        }
        
        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 5mm;
            background: white;
            page-break-inside: auto;
        }
        
        .items-table th {
            background: #28a745;
            color: white;
            padding: 4mm;
            text-align: left;
            font-weight: bold;
            border: 1px solid #1e7e34;
        }
        
        .items-table td {
            padding: 3mm;
            border: 1px solid #ddd;
            color: #1a1a1a;
        }
        
        .items-table tr {
            page-break-inside: avoid;
            page-break-after: auto;
        }
        
        .items-table thead {
            display: table-header-group;
        }
        
        .items-table tbody {
            display: table-row-group;
        }
        
        .items-table tr:nth-child(even) {
            background: #f8f9fa;
        }
        
        .items-table tr:nth-child(odd) {
            background: white;
        }
        
        .total-section {
            margin-top: 5mm;
            padding: 4mm;
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 3px;
        }
        
        .total-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 2mm;
            font-size: 13px;
            font-weight: bold;
        }
        
        .total-label {
            color: #856404;
        }
        
        .total-value {
            color: #0066cc;
        }
        
        .final-total {
            font-size: 16px;
            color: #cc0000;
            border-top: 2px solid #cc0000;
            padding-top: 2mm;
            margin-top: 2mm;
        }
        
        .footer {
            margin-top: 8mm;
            padding-top: 3mm;
            border-top: 1px solid #ddd;
            font-size: 10px;
            color: #666;
        }
        
        .footer-row {
            margin-bottom: 1mm;
        }
        
        .footer-label {
            font-weight: bold;
            color: #0066cc;
        }
    </style>
</head>
<body>"""
        
        for invoice in invoices:
            # Build edit log history HTML if it exists
            edit_log_html = ''
            if invoice.get('edit_log_history'):
                edit_log_value = invoice.get('edit_log_history', 'None')
                edit_log_html = f'<div class="meta-row"><span class="meta-label">EDIT LOG HISTORY:</span><span class="meta-value" style="font-size: 10px;">{edit_log_value}</span></div>'
            
            html += f"""
    <div class="page">
        <div class="form">
            <div class="header">
                <div class="company-name">MOMINA LACE DYEING</div>
                <div class="logo">{logo_html}</div>
                <div class="owner-info">
                    Owner : GHULAM MUSTAFA<br>
                    GM : Shahid, Naveed
                </div>
            </div>
            
            <div class="subtitle">INVOICE</div>
            
            <div class="meta-info">
                <div class="meta-row">
                    <span class="meta-label">INVOICE #:</span>
                    <span class="meta-value">{invoice.get('invoice_number', '')}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">MS PARTY:</span>
                    <span class="meta-value">{invoice.get('ms_party_name', '')}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">DATE:</span>
                    <span class="meta-value">{invoice.get('invoice_date', '')[:10] if invoice.get('invoice_date') else ''}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">CREATED BY:</span>
                    <span class="meta-value">{invoice.get('created_by', '')}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">EDITED BY:</span>
                    <span class="meta-value">{invoice.get('edited_by', 'None') if invoice.get('edited_by') else 'None'}</span>
                </div>
                {edit_log_html}
            </div>
            
            <div class="outward-section">
                <div class="outward-header">OUTWARD DOCUMENTS INFORMATION</div>
                <table class="items-table">
                    <thead>
                        <tr>
                            <th>Outward#/Transfer#</th>
                            <th>GP #</th>
                            <th>Item Name</th>
                            <th>Yards</th>
                            <th>Quantity</th>
                            <th>Rate</th>
                            <th>Amount</th>
                        </tr>
                    </thead>
                    <tbody>"""
            
            # Group items by document (outward or transfer)
            # IMPORTANT: Use composite key (doc_type, doc_id) to avoid conflicts when outward and transfer have same ID
            document_groups = {}
            for item in invoice.get('items', []):
                # Get document type - prioritize explicit document_type field
                doc_type = item.get('document_type', 'outward')
                if not doc_type or doc_type not in ['outward', 'transfer']:
                    # Fallback: determine from which ID is present
                    if item.get('transfer_document_id'):
                        doc_type = 'transfer'
                    else:
                        doc_type = 'outward'
                
                # Get document ID - must have exactly one
                doc_id = item.get('outward_document_id') or item.get('transfer_document_id')
                if doc_id is None:
                    # Skip items without a valid document ID
                    print(f"Warning: Invoice item missing document ID: {item}")
                    continue
                
                # Get document number - prioritize document_number from API, then fallback to specific fields
                doc_number = item.get('document_number', '')
                if not doc_number:
                    if doc_type == 'transfer':
                        doc_number = item.get('transfer_number', '')
                    else:
                        doc_number = item.get('outward_number', '')
                
                # Use composite key (doc_type, doc_id) to ensure transfers and outwards with same ID are separate
                group_key = (doc_type, doc_id)
                if group_key not in document_groups:
                    document_groups[group_key] = {
                        'document_type': doc_type,
                        'document_number': doc_number,
                        'gp_number': item.get('gp_number', ''),
                        'items': []
                    }
                document_groups[group_key]['items'].append(item)
            
            # Sort document groups to ensure consistent ordering (outwards first, then transfers)
            sorted_groups = sorted(document_groups.items(), key=lambda x: (
                0 if x[1]['document_type'] == 'outward' else 1,  # Outwards first
                x[0][1]  # Then by document ID (x[0] is (doc_type, doc_id) tuple)
            ))
            
            for group_key, doc_data in sorted_groups:
                for idx, item in enumerate(doc_data['items']):
                    # Show document number only in first row of each group
                    doc_number_display = doc_data['document_number'] if idx == 0 else ''
                    gp_number_display = doc_data['gp_number'] if idx == 0 else ''
                    html += f"""
                        <tr>
                            <td>{doc_number_display}</td>
                            <td>{gp_number_display}</td>
                            <td>{item.get('item_name', '')}</td>
                            <td>{item.get('measurement', '')}</td>
                            <td>{item.get('quantity', 0):.2f}</td>
                            <td>{item.get('rate', 0):.2f}</td>
                            <td>{item.get('amount', 0):.2f}</td>
                        </tr>"""
            
            # Calculate totals
            subtotal = sum(item.get('amount', 0) for item in invoice.get('items', []))
            discount = invoice.get('discount_amount', 0)
            final_total = invoice.get('total_amount', 0)
            
            html += f"""
                    </tbody>
                </table>
            </div>
            
            <div class="total-section">
                <div class="total-row">
                    <span class="total-label">Sub Total:</span>
                    <span class="total-value">{subtotal:.2f}</span>
                </div>
                <div class="total-row">
                    <span class="total-label">Discount:</span>
                    <span class="total-value">{discount:.2f}</span>
                </div>
                <div class="total-row final-total">
                    <span class="total-label">TOTAL AMOUNT:</span>
                    <span class="total-value">{final_total:.2f}</span>
                </div>
            </div>
            
            <div class="footer">
                <div class="footer-row">
                    <span class="footer-label">SITE:</span> Small Industrial State, Sargodha Road, Faisalabad
                </div>
                <div class="footer-row">
                    <span class="footer-label">CONTACTS:</span> 0321-7651815, 0300-8651815, 0304-6166663, 0300-8636129
                </div>
            </div>
        </div>
    </div>"""
        
        html += """
</body>
</html>"""
        
        return html


# ==================== PRINT INVOICE DIALOG ====================

class PrintInvoiceDialog(QDialog):
    """Dialog for selecting invoices to print"""
    
    def __init__(self, parent=None, selected_rows=None, all_invoices=None):
        super().__init__(parent)
        self.selected_ids = []
        self.all_invoices = all_invoices or []
        self.selected_rows = selected_rows or set()
        self.setWindowTitle("Print Invoice Documents")
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
        instructions = QLabel("Select invoice documents to print:")
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
        
        # Populate list with all invoices
        for idx, invoice in enumerate(self.all_invoices):
            item_text = f"{invoice.get('invoice_number', '')} - {invoice.get('ms_party_name', '')} - {invoice.get('invoice_date', '')[:10]}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, invoice.get('id'))
            
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
                background-color: #dc3545;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
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
        """Get list of selected invoice IDs"""
        selected_ids = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                invoice_id = item.data(Qt.UserRole)
                if invoice_id:
                    selected_ids.append(invoice_id)
        return selected_ids


# ==================== INVOICE DIALOG ====================

class InvoiceDialog(QDialog):
    """Dialog for creating invoices with multi-step flow"""
    
    def __init__(self, parent=None, user_data=None, preselected_party=None, party_rates=None, invoice_id=None):
        super().__init__(parent)
        self.user_data = user_data
        self.api_client = APIClient()
        # Set username on API client for edited_by tracking
        if user_data and user_data.get('username'):
            self.api_client.set_username(user_data.get('username'))
        self.saved_invoice = None  # summary invoice returned by server for instant UI patching
        self.invoice_id = invoice_id  # None for create, invoice_id for edit
        self.is_edit_mode = invoice_id is not None
        self.selected_ms_party = preselected_party  # Pre-selected from search dialog
        self.preselected_party = preselected_party  # Store flag to know if party was pre-selected
        self.selected_outwards = []
        self.invoice_items = []
        self.party_rates = party_rates or {}  # Store party rates for auto-fetch (passed from search dialog)
        self.party_discount = 0.0
        self.current_invoice_outward_ids = []  # Store current invoice outward IDs for edit mode
        self.invoice_date = None  # Store original invoice date for edit mode
        self.current_step = 2 if preselected_party else 1  # Start at step 2 if party pre-selected
        self.setWindowTitle("Edit Invoice" if self.is_edit_mode else "Create Invoice")
        self.setMinimumSize(900, 700)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        self.init_ui()
        
        # If edit mode, load invoice data
        if self.is_edit_mode:
            self.load_invoice_data()
        else:
            # Load parties only if rates not provided
            if not party_rates:
                self.load_ms_parties()
            else:
                # Set discount if party is pre-selected and rates are available
                if preselected_party and preselected_party['id'] in self.party_rates:
                    self.party_discount = self.party_rates[preselected_party['id']]['discount_percent']
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Step indicator
        self.step_label = QLabel("Step 1: Select MS Party")
        self.step_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4;")
        layout.addWidget(self.step_label)
        
        # Main content area (will be updated based on step)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_widget.setLayout(self.content_layout)
        layout.addWidget(self.content_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.back_btn = QPushButton("Back")
        self.back_btn.setEnabled(False)
        self.back_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #666666;
            }
        """)
        self.back_btn.clicked.connect(self.go_back)
        button_layout.addWidget(self.back_btn)
        
        self.next_btn = QPushButton("Next")
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.next_btn.clicked.connect(self.go_next)
        button_layout.addWidget(self.next_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
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
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Show appropriate step based on whether party is pre-selected
        if self.selected_ms_party:
            self.show_step_2()  # Start at step 2 if party already selected
        else:
            self.show_step_1()  # Otherwise start at step 1
    
    def show_step_1(self):
        """Step 1: Select MS Party"""
        self.current_step = 1
        self.step_label.setText("Step 1: Select MS Party")
        self.next_btn.setText("Next")
        self.back_btn.setEnabled(False)  # No step before step 1
        
        # Clear content
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Instructions
        instructions = QLabel("Click 'Next' to search and select MS Party")
        instructions.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
        self.content_layout.addWidget(instructions)
        
        # Show selected party if any
        if self.selected_ms_party:
            selected_label = QLabel(f"Selected: {self.selected_ms_party['name']}")
            selected_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #0078d4;")
            self.content_layout.addWidget(selected_label)
        
        self.content_layout.addStretch()
    
    def show_step_2(self):
        """Step 2: Select Outwards"""
        self.current_step = 2
        self.step_label.setText("Step 2: Select Outward Documents")
        self.next_btn.setText("Make Invoice")
        self.back_btn.setEnabled(True)
        
        # Clear content
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Instructions
        instructions = QLabel("Select one or more outward documents to include in this invoice:")
        instructions.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
        self.content_layout.addWidget(instructions)
        
        # Outward list
        self.outward_list = QListWidget()
        self.outward_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.outward_list.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        self.content_layout.addWidget(self.outward_list)
        
        # Load outwards for selected MS Party
        self.load_outwards()
    
    def show_step_3(self):
        """Step 3: Invoice Items and Finalize"""
        self.current_step = 3
        self.step_label.setText("Step 3: Review Items and Finalize")
        self.next_btn.setText("Save Invoice")
        # Enable back button to go back to step 2
        self.back_btn.setEnabled(True)
        
        # Clear content
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Generate invoice items from selected outwards
        # In edit mode, reload party rates to get latest from backend
        if self.is_edit_mode:
            self.load_ms_parties()
        self.generate_invoice_items()
        
        # Items table
        items_label = QLabel("Invoice Items:")
        items_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.content_layout.addWidget(items_label)
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels([
            "Item Description", "Yards", "Quantity", "Rate", "Amount"
        ])
        # Set column widths - more space for description, less for amount
        self.items_table.setColumnWidth(0, 400)  # Item Description - more space
        self.items_table.setColumnWidth(1, 100)  # Measurement
        self.items_table.setColumnWidth(2, 100)  # Quantity
        self.items_table.setColumnWidth(3, 120)  # Rate
        self.items_table.setColumnWidth(4, 100)  # Amount - less space
        self.items_table.horizontalHeader().setStretchLastSection(False)
        self.items_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        self.items_table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                gridline-color: #3d3d3d;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                padding: 12px 15px;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        self.content_layout.addWidget(self.items_table)
        
        # Totals section
        totals_layout = QFormLayout()
        totals_layout.setSpacing(10)
        
        self.subtotal_label = QLabel("0.00")
        self.subtotal_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        totals_layout.addRow("Sub Total:", self.subtotal_label)
        
        discount_layout = QHBoxLayout()
        self.discount_input = QDoubleSpinBox()
        self.discount_input.setMaximum(100.0)  # Max 100% for percentage
        self.discount_input.setDecimals(2)
        self.discount_input.setSuffix(" %")  # Add % suffix
        self.discount_input.setValue(self.party_discount)  # This is already in percentage
        self.discount_input.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2a2a2a;
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
            }
            QDoubleSpinBox:hover {
                border: 2px solid #0078d4;
            }
        """)
        self.discount_input.valueChanged.connect(self.update_totals)
        discount_layout.addWidget(self.discount_input)
        totals_layout.addRow("Discount (%):", discount_layout)
        
        self.total_label = QLabel("0.00")
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4;")
        totals_layout.addRow("Final Total:", self.total_label)
        
        totals_widget = QWidget()
        totals_widget.setLayout(totals_layout)
        totals_widget.setStyleSheet("background-color: #2a2a2a; padding: 15px; border-radius: 6px;")
        self.content_layout.addWidget(totals_widget)
        
        # Populate items table
        self.populate_items_table()
        self.update_totals()
    
    def load_ms_parties(self):
        """Load MS parties and store rates for later use"""
        try:
            response = requests.get(f"{CLIENT_FALLBACK_SERVER}/api/parties", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    parties = data.get("parties", [])
                    parties = [p for p in parties if p.get('is_active', True)]
                    for party in parties:
                        # Store rates for later use
                        self.party_rates[party['id']] = {
                            'rate_15_yards': party.get('rate_15_yards', 0),
                            'rate_22_yards': party.get('rate_22_yards', 0),
                            'discount_percent': party.get('discount_percent', 0)
                        }
        except Exception as e:
            error_msg = str(e)
            print(f"[InvoiceModule] EXCEPTION in load_ms_parties (InvoiceDialog): {type(e).__name__}: {error_msg}")
            print("[InvoiceModule] Full traceback:")
            traceback.print_exc(file=sys.stdout)
            QMessageBox.warning(self, "Error", f"Failed to load parties: {error_msg}")
    
    def load_invoice_data(self):
        """Load invoice data for editing"""
        try:
            response = requests.get(
                f"{CLIENT_FALLBACK_SERVER}/api/invoice/{self.invoice_id}",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    invoice = data.get("invoice", {})
                    
                    # Set MS Party
                    self.selected_ms_party = {
                        'id': invoice.get('ms_party_id'),
                        'name': invoice.get('ms_party_name', '')
                    }
                    
                    # Load party rates first (synchronous for now)
                    self.load_ms_parties()
                    
                    # Store current invoice outward document IDs and their rates
                    items = invoice.get('items', [])
                    self.current_invoice_outward_ids = list(set([item.get('outward_document_id') for item in items if item.get('outward_document_id')]))
                    
                    # Store existing rates for items in this invoice
                    self.existing_item_rates = {}
                    for item in items:
                        # Use doc_id, item_name, and measurement as key
                        doc_id = item.get('outward_document_id') or item.get('transfer_document_id')
                        doc_type = item.get('document_type', 'outward')
                        key = (doc_type, doc_id, item.get('item_name'), item.get('measurement'))
                        self.existing_item_rates[key] = item.get('rate', 0.0)
                    
                    # Set discount - try to get from backend first, otherwise calculate from amount
                    party_id = invoice.get('ms_party_id')
                    if party_id in self.party_rates:
                        # Use backend discount percentage
                        self.party_discount = self.party_rates[party_id]['discount_percent']
                    else:
                        # Calculate from amount if backend not available
                        discount_amount = invoice.get('discount_amount', 0)
                        subtotal = sum(item.get('amount', 0) for item in items)
                        if subtotal > 0:
                            self.party_discount = (discount_amount / subtotal) * 100.0
                        else:
                            self.party_discount = 0.0
                    
                    # Store original invoice date for edit mode
                    invoice_date_str = invoice.get('invoice_date', '')
                    if invoice_date_str:
                        # Extract date part (YYYY-MM-DD) if it includes time
                        if 'T' in invoice_date_str:
                            invoice_date_str = invoice_date_str.split('T')[0]
                        self.invoice_date = invoice_date_str
                    
                    # Start at step 2 (outward selection)
                    self.current_step = 2
                    self.show_step_2()
                else:
                    QMessageBox.warning(self, "Error", "Failed to load invoice data")
            else:
                QMessageBox.warning(self, "Error", f"Failed to load invoice: {response.status_code}")
        except Exception as e:
            error_msg = str(e)
            print(f"[InvoiceModule] EXCEPTION in load_invoice_data: {type(e).__name__}: {error_msg}")
            print("[InvoiceModule] Full traceback:")
            traceback.print_exc(file=sys.stdout)
            QMessageBox.critical(self, "Error", f"Failed to load invoice data: {error_msg}")
    
    def load_outwards(self):
        """Load available outwards for selected MS Party"""
        if not self.selected_ms_party:
            return
        
        self.outward_list.clear()
        try:
            # If edit mode, include current invoice outwards
            url = f"{CLIENT_FALLBACK_SERVER}/api/invoice/outwards/{self.selected_ms_party['id']}"
            params = {}
            if self.is_edit_mode and self.invoice_id:
                params['exclude_invoice_id'] = self.invoice_id
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    outwards = data.get("outwards", [])
                    if not outwards:
                            # Show message if no documents found
                        no_outwards_label = QLabel("No outward documents available for this MS Party.")
                        no_outwards_label.setStyleSheet("font-size: 14px; color: #888888; padding: 20px;")
                        self.content_layout.addWidget(no_outwards_label)
                    else:
                        for doc in outwards:
                            doc_type = doc.get('document_type', 'outward')
                            doc_number = doc.get('outward_number') or doc.get('document_number', '')
                            
                            # Format display text (only outwards are allowed for invoices)
                            item_text = f"📤 OUTWARD: {doc_number} | GP#: {doc.get('gp_number', '')} | Date: {doc.get('document_date', '')[:10]} | Qty: {doc.get('total_quantity', 0)}"
                            
                            item = QListWidgetItem(item_text)
                            item.setData(Qt.UserRole, doc)
                            self.outward_list.addItem(item)
                            
                            # Pre-select documents that are in current invoice (edit mode)
                            doc_id = doc.get('id')
                            if self.is_edit_mode:
                                if doc_type == 'outward' and doc_id in self.current_invoice_outward_ids:
                                    item.setSelected(True)
                else:
                    QMessageBox.warning(self, "Error", "Failed to load outwards from server")
            else:
                error_msg = f"Server error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", error_msg)
                except:
                    pass
                QMessageBox.warning(self, "Error", f"Failed to load outwards: {error_msg}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load outwards: {str(e)}")
    
    def generate_invoice_items(self):
        """Generate invoice items from selected outwards (transfers are not invoiced)."""
        self.invoice_items = []
        
        for doc_data in self.selected_outwards:
            doc_id = doc_data.get('id')
            doc_type = doc_data.get('document_type', 'outward')

            # Business rule (2026-01): transfers are not allowed on invoices
            if doc_type == 'transfer':
                continue
            
            try:
                # Determine API endpoint (outwards only)
                endpoint = f"{CLIENT_FALLBACK_SERVER}/api/invoice/outward/{doc_id}/items"
                
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        items = data.get("items", [])
                        for item in items:
                            # Each item becomes one invoice row
                            invoice_item = {
                                'outward_document_id': None,
                                'transfer_document_id': None,
                                'document_type': doc_type,
                                'outward_number': item.get('outward_number', ''),
                                'transfer_number': '',  # Not used now that transfers are not invoiced
                                'gp_number': item.get('gp_number', ''),
                                'item_name': item.get('item_name', ''),
                                'measurement': item.get('measurement', 15),
                                'quantity': item.get('quantity', 0),
                                'rate': 0.0,  # Will be fetched or entered manually
                                'amount': 0.0  # Will be calculated
                            }
                            
                            invoice_item['outward_document_id'] = doc_id
                            invoice_item['outward_number'] = doc_data.get('outward_number') or doc_data.get('document_number', '')
                            
                            self.invoice_items.append(invoice_item)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load items for outward {doc_id}: {str(e)}")
        
        # Auto-fetch rates for each item and track which rates are from backend
        party_id = self.selected_ms_party['id']
        self.rate_from_backend = {}  # Track which rates came from backend (non-zero)
        
        # Reload party rates to get latest from backend (important for edit mode)
        if not self.party_rates or party_id not in self.party_rates:
            self.load_ms_parties()
        
        if party_id in self.party_rates:
            rates = self.party_rates[party_id]
            for idx, item in enumerate(self.invoice_items):
                # 1. First priority: Check if this item already exists in the invoice being edited
                doc_id = item.get('outward_document_id') or item.get('transfer_document_id')
                doc_type = item.get('document_type', 'outward')
                key = (doc_type, doc_id, item.get('item_name'), item.get('measurement'))
                
                if self.is_edit_mode and hasattr(self, 'existing_item_rates') and key in self.existing_item_rates:
                    item['rate'] = self.existing_item_rates[key]
                    self.rate_from_backend[idx] = True # Mark as "provided" but we'll make it editable
                    item['amount'] = item['quantity'] * item['rate']
                    continue

                # 2. Second priority: Use backend party rates
                measurement = item['measurement']
                if measurement == 15:
                    backend_rate = rates['rate_15_yards'] if rates['rate_15_yards'] > 0 else 0.0
                    item['rate'] = backend_rate
                    if backend_rate > 0:
                        self.rate_from_backend[idx] = True
                    else:
                        self.rate_from_backend[idx] = False
                elif measurement == 22:
                    backend_rate = rates['rate_22_yards'] if rates['rate_22_yards'] > 0 else 0.0
                    item['rate'] = backend_rate
                    if backend_rate > 0:
                        self.rate_from_backend[idx] = True
                    else:
                        self.rate_from_backend[idx] = False
                item['amount'] = item['quantity'] * item['rate']
        else:
            # No rates available, all can be edited
            for idx in range(len(self.invoice_items)):
                self.rate_from_backend[idx] = False
        
        # Update discount from backend in edit mode
        if self.is_edit_mode and party_id in self.party_rates:
            self.party_discount = self.party_rates[party_id]['discount_percent']
        elif not self.is_edit_mode and party_id in self.party_rates:
            self.party_discount = self.party_rates[party_id]['discount_percent']
    
    def populate_items_table(self):
        """Populate items table with invoice items"""
        self.items_table.setRowCount(len(self.invoice_items))
        
        for row, item in enumerate(self.invoice_items):
            # Item Description: Outward documents only
            doc_number = item.get('outward_number', '')
            desc = f"Outward#: {doc_number} | GP#: {item['gp_number']} | {item['item_name']}"
            desc_item = QTableWidgetItem(desc)
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
            desc_item.setBackground(Qt.darkGray)
            self.items_table.setItem(row, 0, desc_item)
            
            # Measurement
            meas_item = QTableWidgetItem(f"{item['measurement']}")
            meas_item.setFlags(meas_item.flags() & ~Qt.ItemIsEditable)
            meas_item.setBackground(Qt.darkGray)
            self.items_table.setItem(row, 1, meas_item)
            
            # Quantity
            qty_item = QTableWidgetItem(f"{item['quantity']:.2f}")
            qty_item.setFlags(qty_item.flags() & ~Qt.ItemIsEditable)
            qty_item.setBackground(Qt.darkGray)
            self.items_table.setItem(row, 2, qty_item)
            
            # Rate (always editable per user request)
            rate_item = QTableWidgetItem(f"{item['rate']:.2f}")
            rate_item.setData(Qt.UserRole, row)  # Store row index
            self.items_table.setItem(row, 3, rate_item)
            
            # Amount (calculated, but editable for manual override)
            amount_item = QTableWidgetItem(f"{item['amount']:.2f}")
            amount_item.setData(Qt.UserRole, row)
            self.items_table.setItem(row, 4, amount_item)
        
        # Connect item changed signal
        self.items_table.itemChanged.connect(self.on_item_changed)
    
    def on_item_changed(self, item):
        """Handle item changes in table"""
        row = item.data(Qt.UserRole)
        if row is None:
            return
        
        if row >= len(self.invoice_items):
            return
        
        col = item.column()
        invoice_item = self.invoice_items[row]
        
        if col == 3:  # Rate changed
            try:
                new_rate = float(item.text())
                invoice_item['rate'] = new_rate
                # Recalculate amount
                invoice_item['amount'] = invoice_item['quantity'] * new_rate
                # Update amount cell
                amount_item = self.items_table.item(row, 4)
                if amount_item:
                    amount_item.setText(f"{invoice_item['amount']:.2f}")
                self.update_totals()
            except ValueError:
                pass
        
        elif col == 4:  # Amount changed (manual override)
            try:
                new_amount = float(item.text())
                invoice_item['amount'] = new_amount
                self.update_totals()
            except ValueError:
                pass
    
    def update_totals(self):
        """Update subtotal, discount, and final total"""
        subtotal = sum(item['amount'] for item in self.invoice_items)
        
        # Discount is in percentage, convert to amount
        discount_percent = self.discount_input.value()
        if discount_percent == 0.0 and self.party_discount > 0:
            # Auto-fill discount percentage if available
            self.discount_input.blockSignals(True)
            self.discount_input.setValue(self.party_discount)
            self.discount_input.blockSignals(False)
            discount_percent = self.party_discount
        
        # Calculate discount amount from percentage
        discount_amount = subtotal * (discount_percent / 100.0)
        final_total = subtotal - discount_amount
        
        self.subtotal_label.setText(f"{subtotal:.2f}")
        self.total_label.setText(f"{final_total:.2f}")
    
    def go_next(self):
        """Move to next step"""
        if self.current_step == 1:
            # This should not happen if party is pre-selected, but handle it anyway
            if not self.selected_ms_party:
                # Show search dialog for MS Party
                search_dialog = MSPartySearchDialog(self, self.party_rates)
                if search_dialog.exec_() == QDialog.Accepted:
                    selected_party = search_dialog.selected_party
                    if selected_party:
                        self.selected_ms_party = selected_party
                        self.show_step_2()  # Go directly to step 2
                    else:
                        QMessageBox.warning(self, "Validation", "Please select an MS Party")
                        return
                else:
                    return  # User cancelled
            else:
                # Party already selected, go to step 2
                self.show_step_2()
        
        elif self.current_step == 2:
            # Validate outward selection
            selected_items = self.outward_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Validation", "Please select at least one outward document")
                return
            
            # Store selected outwards
            self.selected_outwards = []
            for item in selected_items:
                self.selected_outwards.append(item.data(Qt.UserRole))
            
            self.show_step_3()
        
        elif self.current_step == 3:
            # Save invoice
            self.save_invoice()
    
    def go_back(self):
        """Move to previous step"""
        if self.current_step == 2:
            # Go back to step 1 (show step 1 even if party was pre-selected)
            self.show_step_1()
        elif self.current_step == 3:
            # Go back to step 2 (outward selection)
            self.show_step_2()
    
    def save_invoice(self):
        """Save invoice to database"""
        # Validate items
        if not self.invoice_items:
            QMessageBox.warning(self, "Validation", "No items to invoice")
            return
        
        # Prepare request
        invoice_items_data = []
        for item in self.invoice_items:
            invoice_items_data.append({
                'outward_document_id': item.get('outward_document_id'),
                'transfer_document_id': item.get('transfer_document_id'),
                'item_name': item['item_name'],
                'measurement': item['measurement'],
                'quantity': item['quantity'],
                'rate': item['rate'],
                'amount': item['amount']
            })
        
        # Collect outward IDs for backward compatibility (transfers are not invoiced)
        outward_ids = []
        for doc in self.selected_outwards:
            if doc.get('document_type') == 'transfer':
                # Transfers don't go in outward_document_ids
                continue
            outward_ids.append(doc['id'])
        
        # Calculate discount amount from percentage
        discount_percent = self.discount_input.value()
        subtotal = sum(item['amount'] for item in self.invoice_items)
        discount_amount = subtotal * (discount_percent / 100.0)
        
        # Use original invoice date if editing, otherwise use current date
        if self.is_edit_mode and self.invoice_date:
            invoice_date_str = self.invoice_date
        else:
            invoice_date_str = QDate.currentDate().toString("yyyy-MM-dd")
        
        request_data = {
            'ms_party_id': self.selected_ms_party['id'],
            'outward_document_ids': outward_ids,
            'items': invoice_items_data,
            'discount_amount': discount_amount,  # Store as amount in database
            'discount_source': 'auto' if self.party_discount > 0 else 'manual',
            'invoice_date': invoice_date_str
        }
        
        try:
            if self.is_edit_mode:
                # Update existing invoice
                request_data['invoice_id'] = self.invoice_id
                response = self.api_client._try_request_with_retry("PUT", f"/api/invoice/{self.invoice_id}", json=request_data)
                success_msg = "Invoice updated successfully"
                error_msg = "Failed to update invoice"
            else:
                # Create new invoice
                request_data['created_by'] = self.user_data.get('username', 'Unknown') if self.user_data else 'Unknown'
                response = self.api_client._try_request_with_retry("POST", "/api/invoice", json=request_data)
                success_msg = "Invoice created successfully"
                error_msg = "Failed to create invoice"
            
            if response and response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    QMessageBox.information(self, "Success", success_msg)
                    if isinstance(data.get("invoice"), dict):
                        self.saved_invoice = data.get("invoice")
                    self.accept()
                else:
                    QMessageBox.warning(self, "Error", data.get("message", error_msg))
            elif response is None:
                # Connection failed after all retries
                QMessageBox.warning(
                    self, "Connection Error",
                    "Unable to connect to the server after multiple attempts.\n\n"
                    "Please check your network connection and try again.\n"
                    "Your data has been preserved in the form."
                )
            else:
                error_detail = error_msg
                try:
                    if response:
                        error_data = response.json() if response.content else {}
                        error_detail = error_data.get("detail", error_msg)
                except Exception:
                    pass
                QMessageBox.warning(self, "Error", error_detail)
        except Exception as e:
            error_msg_detail = str(e)
            print(f"[InvoiceModule] EXCEPTION in save_invoice: {type(e).__name__}: {error_msg_detail}")
            print("[InvoiceModule] Full traceback:")
            traceback.print_exc(file=sys.stdout)
            QMessageBox.critical(self, "Error", f"{error_msg}: {error_msg_detail}")


# ==================== MS PARTY SEARCH DIALOG ====================

class MSPartySearchDialog(QDialog):
    """Small search dialog for selecting MS Party with autocomplete"""
    
    def __init__(self, parent=None, party_rates=None):
        super().__init__(parent)
        self.selected_party = None
        self.party_rates = {}  # Will be populated when loading parties
        self.setWindowTitle("Search MS Party")
        self.setMinimumSize(450, 180)
        self.setMaximumSize(550, 220)
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Label
        label = QLabel("Search MS Party:")
        label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(label)
        
        # Search input with autocomplete
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search MS Party...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2a2a2a;
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                padding: 10px;
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        # Allow Enter key to accept selection
        self.search_input.returnPressed.connect(self.accept_selection)
        layout.addWidget(self.search_input)
        
        # Buttons
        button_layout = QHBoxLayout()
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
        
        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        ok_btn.clicked.connect(self.accept_selection)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_parties(self):
        """Load MS parties for autocomplete"""
        try:
            response = requests.get(f"{CLIENT_FALLBACK_SERVER}/api/parties", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    parties = data.get("parties", [])
                    parties = [p for p in parties if p.get('is_active', True)]
                    party_names = [party['name'] for party in parties]
                    
                    # Store party data for lookup
                    self.parties_dict = {party['name']: party for party in parties}
                    
                    # Store party rates for passing to invoice dialog
                    for party in parties:
                        self.party_rates[party['id']] = {
                            'rate_15_yards': party.get('rate_15_yards', 0),
                            'rate_22_yards': party.get('rate_22_yards', 0),
                            'discount_percent': party.get('discount_percent', 0)
                        }
                    
                    # Setup autocomplete
                    completer = QCompleter(party_names, self.search_input)
                    completer.setCaseSensitivity(Qt.CaseInsensitive)
                    completer.setCompletionMode(QCompleter.PopupCompletion)
                    completer.setFilterMode(Qt.MatchContains)
                    completer.setMaxVisibleItems(10)
                    self.search_input.setCompleter(completer)
                    
                    # Style the completer popup
                    completer.popup().setStyleSheet("""
                        QListView {
                            background-color: #2a2a2a;
                            color: #ffffff;
                            border: 1px solid #3d3d3d;
                        }
                        QListView::item {
                            padding: 5px;
                        }
                        QListView::item:selected {
                            background-color: #0078d4;
                        }
                    """)
        except Exception as e:
            error_msg = str(e)
            print(f"[InvoiceModule] EXCEPTION in load_parties (MSPartySearchDialog): {type(e).__name__}: {error_msg}")
            print("[InvoiceModule] Full traceback:")
            traceback.print_exc(file=sys.stdout)
            QMessageBox.warning(self, "Error", f"Failed to load parties: {error_msg}")
    
    def accept_selection(self):
        """Accept the selected party"""
        party_name = self.search_input.text().strip()
        if not party_name:
            QMessageBox.warning(self, "Validation", "Please enter an MS Party name")
            return
        
        # Find party by name
        if hasattr(self, 'parties_dict') and party_name in self.parties_dict:
            party = self.parties_dict[party_name]
            self.selected_party = {
                'id': party['id'],
                'name': party['name']
            }
            self.accept()
        else:
            QMessageBox.warning(self, "Validation", f"MS Party '{party_name}' not found. Please select from suggestions.")

