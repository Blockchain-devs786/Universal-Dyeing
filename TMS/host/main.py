"""TMS Host Application Main Entry Point"""

import sys
import os
import threading
from pathlib import Path

# Add project root to Python path
# Handle PyInstaller executable path
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(sys.executable).parent
    # Add base path to sys.path
    if str(base_path) not in sys.path:
        sys.path.insert(0, str(base_path))
    # Also add common and host directories if they exist
    for module_dir in ['common', 'host']:
        module_path = base_path / module_dir
        if module_path.exists() and str(module_path) not in sys.path:
            sys.path.insert(0, str(module_path))
else:
    # Running as script
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from host.license_manager import LicenseManager
from host.db_pool import db_pool
from host.api_server import start_api_server
from host.ui.license_dialog import LicenseDialog
from host.ui.admin_setup_dialog import AdminSetupDialog
from host.ui.login_dialog import LoginDialog
from host.ui.dashboard import DashboardWindow
from common.config import API_HOST, API_PORT


def check_admin_exists():
    """Check if admin user exists"""
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE role = 'ADMIN'")
        exists = cursor.fetchone() is not None
        cursor.close()
        return exists
    except Exception:
        return False
    finally:
        if conn:
            db_pool.return_connection(conn)


def main():
    """Main application entry point"""
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        # Initialize license manager
        license_manager = LicenseManager()
        
        # Check license status
        if not license_manager.is_valid():
            # Show license dialog
            license_dialog = LicenseDialog()
            if license_dialog.exec_() != LicenseDialog.Accepted:
                print("License activation cancelled or failed")
                sys.exit(0)
            
            # Re-check license after activation
            if not license_manager.is_valid():
                print("License still invalid after activation")
                sys.exit(0)
        
        # Initialize database pool
        print("Initializing database connection pool...")
        if not db_pool.initialize():
            print("ERROR: Failed to initialize database connection pool")
            print("Please ensure MySQL is running and credentials are correct in common/config.py")
            if sys.stdin and sys.stdin.isatty():
                input("Press Enter to exit...")
            sys.exit(1)
        
        # Start API server in background thread
        print(f"Starting API server on http://0.0.0.0:{API_PORT} (accessible via localhost and ZeroTier)...")
        api_thread = threading.Thread(target=start_api_server, daemon=True, name="API_Server_Thread")
        api_thread.start()
        
        # Give API server more time to start (especially in exe)
        import time
        time.sleep(3)  # Increased wait time for server to fully start
        
        # Verify server is running
        max_retries = 5
        server_started = False
        for attempt in range(max_retries):
            try:
                import requests
                # Test localhost (can't connect to 0.0.0.0 directly)
                response = requests.get(f"http://127.0.0.1:{API_PORT}/api/ping", timeout=2)
                if response.status_code == 200:
                    print("[OK] API Server is running and accessible")
                    server_started = True
                    break
                else:
                    print(f"[WARN] API Server ping failed (status: {response.status_code}), retrying...")
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    print(f"[WARN] Server not ready yet, waiting... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(1)
                else:
                    print("[WARN] Could not connect to API server after multiple attempts")
                    print("   The server may still be starting. Try accessing http://localhost:8000/api/ping")
            except Exception as e:
                print(f"[WARN] Error verifying server: {e}")
                break
        
        if not server_started:
            print("[WARN] API Server verification failed, but continuing...")
            print("   Server thread is running. Check http://localhost:8000/api/ping manually")
        
        # Check if admin exists
        if not check_admin_exists():
            # Show admin setup dialog
            admin_dialog = AdminSetupDialog()
            if admin_dialog.exec_() != AdminSetupDialog.Accepted:
                print("Admin setup cancelled")
                sys.exit(0)
        
        # Show login dialog
        login_dialog = LoginDialog()
        if login_dialog.exec_() != LoginDialog.Accepted:
            print("Login cancelled")
            sys.exit(0)
        
        # Show dashboard
        dashboard = DashboardWindow(login_dialog.user_data)
        dashboard.show()
        
        print("Application started successfully!")
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        if sys.stdin and sys.stdin.isatty():
            input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
