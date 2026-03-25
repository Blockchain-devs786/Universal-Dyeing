"""Security utilities for encryption and hashing"""

import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os
from common.config import AES_KEY_SIZE, BCRYPT_ROUNDS


def generate_key_from_machine_id(machine_id: str) -> bytes:
    """Generate AES key from machine ID"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'tms_license_salt_2024',
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
    return key


def encrypt_license_data(data: dict, machine_id: str) -> bytes:
    """Encrypt license data using AES-256"""
    key = generate_key_from_machine_id(machine_id)
    fernet = Fernet(key)
    
    import json
    json_data = json.dumps(data).encode()
    encrypted = fernet.encrypt(json_data)
    return encrypted


def decrypt_license_data(encrypted_data: bytes, machine_id: str) -> dict:
    """Decrypt license data using AES-256"""
    try:
        key = generate_key_from_machine_id(machine_id)
        fernet = Fernet(key)
        
        decrypted = fernet.decrypt(encrypted_data)
        import json
        data = json.loads(decrypted.decode())
        return data
    except Exception:
        return None


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False

