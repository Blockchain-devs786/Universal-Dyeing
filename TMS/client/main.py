"""TMS Client Application Main Entry Point"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from typing import Dict

from client.ui.login_dialog import LoginDialog
from common.ui.main_window import MainApplicationWindow
from client.websocket_client import WebSocketClient
from common.realtime_bus import RealtimeBus
from client.config_loader import load_client_config, get_server_url, show_config_error
from client.api_client import APIClient


def main():
    """Main application entry point"""
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        print("Starting TMS Client...")
        
        # Load client configuration
        config = load_client_config()
        if not config:
            print("[WARN] client_config.json not found or invalid. Using fallback configuration.")
            show_config_error()
        else:
            server_url = get_server_url(config)
            print(f"Connecting to server at {server_url}...")
            
            # Test connection to ZeroTier IP
            api_client = APIClient()
            if not api_client.ping():
                # Show error message if server is unreachable
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Connection Error")
                msg.setText("Cannot connect to server")
                msg.setInformativeText(
                    f"Unable to reach server at {server_url}.\n\n"
                    "Possible reasons:\n"
                    "• ZeroTier is not connected\n"
                    "• Server is down\n"
                    "• Network connectivity issues\n\n"
                    "The application will continue, but you may experience connection issues."
                )
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
        
        # Show login dialog
        login_dialog = LoginDialog()
        if login_dialog.exec_() == LoginDialog.Accepted:
            # Login successful - show main application window with user data
            print("Login successful!")
            user_data = login_dialog.user_data
            
            # Qt-safe real-time bus (messages emitted from WS thread, delivered on UI thread)
            ws_bus = RealtimeBus()
            user_data["ws_bus"] = ws_bus
            
            # Initialize WebSocket client for real-time updates
            def handle_websocket_message(message: Dict):
                """Handle incoming WebSocket messages (called from WS thread)."""
                try:
                    ws_bus.message.emit(message)
                except Exception:
                    # Never let callback crash the WS loop
                    pass
            
            ws_client = WebSocketClient(on_message=handle_websocket_message)
            ws_client.start()
            
            # Store WebSocket client in user_data for access in main window
            user_data['websocket_client'] = ws_client
            
            main_window = MainApplicationWindow(user_data=user_data)
            main_window.show()
            
            try:
                sys.exit(app.exec_())
            finally:
                # Cleanup WebSocket on exit
                ws_client.stop()
        else:
            # Login cancelled or failed - exit immediately
            print("Login cancelled or failed")
            sys.exit(0)
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()

