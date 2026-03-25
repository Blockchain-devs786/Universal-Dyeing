"""Configuration loader for TMS Client"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from PyQt5.QtWidgets import QMessageBox


def load_client_config() -> Optional[Dict]:
    """
    Load client configuration from client_config.json
    
    Returns:
        Dict with config values or None if file doesn't exist or is invalid
    """
    # Look for config file in the same directory as the client module
    config_path = Path(__file__).parent.parent / "client_config.json"
    
    # Also check in current working directory
    if not config_path.exists():
        config_path = Path("client_config.json")
    
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Validate required fields
        required_fields = ["host_zerotier_ip", "port", "timeout"]
        for field in required_fields:
            if field not in config:
                print(f"[CONFIG] Warning: Missing required field '{field}' in config")
                return None
        
        # Validate IP format (basic check)
        ip = config.get("host_zerotier_ip", "")
        if not ip or not isinstance(ip, str):
            print(f"[CONFIG] Warning: Invalid host_zerotier_ip in config")
            return None
        
        # Validate port
        port = config.get("port", 8000)
        if not isinstance(port, int) or port < 1 or port > 65535:
            print(f"[CONFIG] Warning: Invalid port in config: {port}")
            return None
        
        # Validate timeout
        timeout = config.get("timeout", 5)
        if not isinstance(timeout, (int, float)) or timeout < 1:
            print(f"[CONFIG] Warning: Invalid timeout in config: {timeout}")
            return None
        
        print(f"[CONFIG] Loaded config: host={ip}, port={port}, timeout={timeout}")
        return config
        
    except json.JSONDecodeError as e:
        print(f"[CONFIG] Error: Invalid JSON in config file: {e}")
        return None
    except Exception as e:
        print(f"[CONFIG] Error loading config: {e}")
        return None


def get_server_url(config: Optional[Dict] = None) -> str:
    """
    Get server URL from config
    
    Args:
        config: Optional config dict (if None, will load from file)
    
    Returns:
        Server URL string (e.g., "http://10.147.20.100:8000")
    """
    if config is None:
        config = load_client_config()
    
    if config:
        ip = config.get("host_zerotier_ip", "")
        port = config.get("port", 8000)
        return f"http://{ip}:{port}"
    
    # Fallback to localhost if config not available
    return "http://127.0.0.1:8000"


def show_config_error(parent=None):
    """Show error message if config file is missing or invalid"""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle("Configuration Error")
    msg.setText("Client configuration file not found or invalid")
    msg.setInformativeText(
        "Please create 'client_config.json' in the application directory with:\n\n"
        "{\n"
        '  "host_zerotier_ip": "10.xx.xx.xx",\n'
        '  "port": 8000,\n'
        '  "timeout": 5\n'
        "}\n\n"
        "Falling back to localhost connection."
    )
    msg.exec_()

