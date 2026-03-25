"""License Management System"""

import os
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Dict
from common.utils import get_app_data_path, get_machine_id, ensure_directory
from common.security import encrypt_license_data, decrypt_license_data


class LicenseManager:
    """Manages license validation and encryption"""
    
    def __init__(self):
        self.app_data_path = get_app_data_path()
        self.license_path = self.app_data_path / "license.dat"
        self.machine_id = get_machine_id()
        ensure_directory(self.app_data_path)
    
    def _make_file_hidden(self) -> None:
        """Make license file hidden and system protected (Windows)"""
        if os.name == 'nt' and self.license_path.exists():
            try:
                import ctypes
                # Set file as hidden
                ctypes.windll.kernel32.SetFileAttributesW(
                    str(self.license_path),
                    0x02  # FILE_ATTRIBUTE_HIDDEN
                )
            except Exception:
                pass
    
    def get_license(self) -> Optional[Dict]:
        """Get and decrypt license data"""
        if not self.license_path.exists():
            return None
        
        try:
            with open(self.license_path, 'rb') as f:
                encrypted_data = f.read()
            
            data = decrypt_license_data(encrypted_data, self.machine_id)
            if not data:
                return None
            
            # Validate machine ID
            if data.get("machine_id") != self.machine_id:
                return None
            
            # Check expiry and set status correctly
            expiry_str = data.get("expiry_date", "")
            if expiry_str:
                try:
                    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                    today = date.today()
                    if expiry_date < today:
                        data["status"] = "EXPIRED"
                    else:
                        # Explicitly set to VALID if not expired
                        data["status"] = "VALID"
                except Exception as e:
                    print(f"Error parsing expiry date: {e}")
                    data["status"] = "EXPIRED"
            else:
                # No expiry date means expired
                data["status"] = "EXPIRED"
            
            return data
        except Exception as e:
            print(f"Error reading license: {e}")
            return None
    
    def save_license(self, expiry_date: str, license_type: str = "HOST", validity_days: int = 0) -> bool:
        """Save encrypted license data"""
        try:
            # Calculate expiry date if validity_days provided
            if validity_days > 0:
                expiry = (datetime.now() + timedelta(days=validity_days)).date()
                expiry_date = expiry.strftime("%Y-%m-%d")
            
            # Validate expiry_date format
            if not expiry_date:
                print("Error: No expiry date provided")
                return False
            
            try:
                expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            except ValueError as e:
                print(f"Error: Invalid expiry date format: {e}")
                return False
            
            # Determine status based on expiry date
            today = date.today()
            if expiry < today:
                status = "EXPIRED"
            else:
                status = "VALID"
            
            license_data = {
                "machine_id": self.machine_id,
                "expiry_date": expiry_date,
                "license_type": license_type,
                "status": status
            }
            
            encrypted_data = encrypt_license_data(license_data, self.machine_id)
            if not encrypted_data:
                print("Error: Failed to encrypt license data")
                return False
            
            # Ensure directory exists
            ensure_directory(self.app_data_path)
            
            # Try to remove existing file if it exists (in case it's locked)
            if self.license_path.exists():
                try:
                    # Remove hidden attribute first if on Windows
                    if os.name == 'nt':
                        import ctypes
                        ctypes.windll.kernel32.SetFileAttributesW(
                            str(self.license_path),
                            0x80  # FILE_ATTRIBUTE_NORMAL
                        )
                    self.license_path.unlink()
                except Exception as e:
                    print(f"Warning: Could not remove existing license file: {e}")
            
            # Write new license file
            try:
                with open(self.license_path, 'wb') as f:
                    f.write(encrypted_data)
            except PermissionError as e:
                print(f"Error: Permission denied when saving license file: {e}")
                print(f"License path: {self.license_path}")
                return False
            except Exception as e:
                print(f"Error: Failed to write license file: {e}")
                return False
            
            # Make file hidden after writing
            self._make_file_hidden()
            
            # Verify the file was written correctly
            if not self.license_path.exists():
                print("Error: License file was not created")
                return False
            
            return True
        except Exception as e:
            print(f"Error saving license: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def is_valid(self) -> bool:
        """Check if license is valid"""
        license_data = self.get_license()
        if not license_data:
            return False
        
        return license_data.get("status") == "VALID"
    
    def get_status(self) -> str:
        """Get license status"""
        license_data = self.get_license()
        if not license_data:
            return "EXPIRED"
        return license_data.get("status", "EXPIRED")

