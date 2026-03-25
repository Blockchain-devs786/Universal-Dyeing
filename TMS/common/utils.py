"""Utility functions for TMS application"""

import os
import platform
import hashlib
import subprocess
from pathlib import Path


def get_app_data_path() -> Path:
    """Get application data directory path"""
    if platform.system() == "Windows":
        app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
        return Path(app_data) / "TMS"
    else:
        return Path.home() / ".tms"


def get_machine_id() -> str:
    """Generate unique machine ID based on hardware"""
    try:
        # Get CPU serial number
        cpu_info = ""
        if platform.system() == "Windows":
            try:
                cpu_info = subprocess.check_output(
                    'wmic cpu get ProcessorId',
                    shell=True,
                    stderr=subprocess.DEVNULL
                ).decode().strip().split('\n')[1].strip()
            except:
                cpu_info = platform.processor()
        
        # Get disk serial number
        disk_info = ""
        if platform.system() == "Windows":
            try:
                disk_info = subprocess.check_output(
                    'wmic diskdrive get serialnumber',
                    shell=True,
                    stderr=subprocess.DEVNULL
                ).decode().strip().split('\n')[1].strip()
            except:
                disk_info = str(Path.home())
        
        # Get MAC address
        mac_info = ""
        if platform.system() == "Windows":
            try:
                mac_info = subprocess.check_output(
                    'getmac /v /fo list',
                    shell=True,
                    stderr=subprocess.DEVNULL
                ).decode().strip()
            except:
                mac_info = platform.node()
        
        # Combine and hash
        machine_string = f"{cpu_info}|{disk_info}|{mac_info}|{platform.node()}"
        machine_id = hashlib.sha256(machine_string.encode()).hexdigest()
        return machine_id
    except Exception:
        # Fallback to platform node
        return hashlib.sha256(platform.node().encode()).hexdigest()


def ensure_directory(path: Path) -> None:
    """Ensure directory exists"""
    path.mkdir(parents=True, exist_ok=True)

