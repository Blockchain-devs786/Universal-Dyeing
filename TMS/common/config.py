"""Configuration constants for TMS application"""

# API Configuration
# Bind to 0.0.0.0 to accept connections from all interfaces (localhost + ZeroTier)
API_HOST = "0.0.0.0"
API_PORT = 8000
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

# Client API Configuration (with fallback)
CLIENT_PRIMARY_SERVER = "https://api.mominaembroidey.org.uk"
# Note: CLIENT_FALLBACK_SERVER must use 127.0.0.1 (not 0.0.0.0) because 0.0.0.0 is only for server binding
CLIENT_FALLBACK_SERVER = f"http://127.0.0.1:{API_PORT}"

# Database Configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "AzanMalik7860",
    "database": "tms",
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci"
}

# Connection Pool Configuration
POOL_CONFIG = {
    "min_connections": 5,
    "max_connections": 20,
    "timeout": 2,
    "autocommit": True
}

# License Configuration
LICENSE_DIR = "TMS"
LICENSE_FILENAME = "license.dat"

# Email Configuration
EMAIL_ADDRESS = "malikazan8768@gmail.com"
EMAIL_APP_PASSWORD = "tcdh tube oaqz tjng"
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587
EMAIL_IMAP_SERVER = "imap.gmail.com"
EMAIL_IMAP_PORT = 993

# Security
AES_KEY_SIZE = 32  # 256 bits
BCRYPT_ROUNDS = 12

