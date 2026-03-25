"""
Local SQLite Database Manager for TMS Client (Offline-First Architecture)

Creates and manages a local SQLite database at %APPDATA%/TMS/local_data.db.
Tables mirror the host MySQL schema for offline data entry, with a sync_queue
table to track changes that need to be pushed to the server.
"""

import sqlite3
import os
import uuid
import json
import threading
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Database path
# ---------------------------------------------------------------------------

def _get_db_path() -> str:
    """Get the path to the local SQLite database file."""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    db_dir = os.path.join(appdata, "TMS")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "local_data.db")


DB_PATH = _get_db_path()


# ---------------------------------------------------------------------------
# Thread-local connections
# ---------------------------------------------------------------------------

_thread_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """
    Get a thread-local SQLite connection (auto-created on first call per thread).
    Connections use WAL mode for better concurrent read/write performance.
    """
    conn = getattr(_thread_local, "connection", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row          # dict-like row access
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _thread_local.connection = conn
    return conn


def generate_uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def initialize_database():
    """
    Create all tables if they don't exist.
    Safe to call multiple times (uses IF NOT EXISTS).
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ---- session (stores login data) ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            token TEXT,
            modules TEXT,
            logged_in_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---- Reference / master tables (seeded from server on login) ----

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS liabilities (
            id INTEGER PRIMARY KEY,
            uuid TEXT UNIQUE DEFAULT (lower(hex(randomblob(16)))),
            name TEXT NOT NULL,
            rate_15_yards REAL DEFAULT 0.0,
            rate_22_yards REAL DEFAULT 0.0,
            discount_percent REAL DEFAULT 0.0,
            is_active INTEGER DEFAULT 1,
            is_ms_party INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY,
            uuid TEXT UNIQUE DEFAULT (lower(hex(randomblob(16)))),
            name TEXT NOT NULL UNIQUE,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY,
            uuid TEXT UNIQUE DEFAULT (lower(hex(randomblob(16)))),
            name TEXT NOT NULL UNIQUE,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY,
            uuid TEXT UNIQUE DEFAULT (lower(hex(randomblob(16)))),
            name TEXT NOT NULL UNIQUE,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---- Auto-numbering (local counter for document numbers) ----

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auto_numbering (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            counter_type TEXT NOT NULL,
            counter_value INTEGER NOT NULL DEFAULT 0,
            party_name TEXT,
            UNIQUE(counter_type, party_name)
        )
    """)

    # ---- Inward documents ----

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inward_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            inward_number TEXT UNIQUE NOT NULL,
            gp_number TEXT NOT NULL,
            sr_number TEXT,
            ms_party_id INTEGER NOT NULL,
            from_party TEXT,
            vehicle_number TEXT,
            driver_name TEXT,
            total_quantity REAL DEFAULT 0.0,
            document_date TEXT NOT NULL,
            created_by TEXT NOT NULL,
            edited_by TEXT,
            edit_log_history TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ms_party_id) REFERENCES liabilities(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inward_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            inward_document_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            measurement INTEGER NOT NULL,
            quantity REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (inward_document_id) REFERENCES inward_documents(id) ON DELETE CASCADE
        )
    """)

    # ---- Transfer documents ----

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfer_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            transfer_number TEXT UNIQUE NOT NULL,
            gp_number TEXT NOT NULL,
            sr_number TEXT,
            ms_party_id INTEGER NOT NULL,
            from_party TEXT,
            transfer_to TEXT,
            transfer_to_ms_party_id INTEGER,
            vehicle_number TEXT,
            driver_name TEXT,
            total_quantity REAL DEFAULT 0.0,
            transfer_type TEXT DEFAULT 'simple',
            document_date TEXT NOT NULL,
            created_by TEXT NOT NULL,
            edited_by TEXT,
            edit_log_history TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ms_party_id) REFERENCES liabilities(id),
            FOREIGN KEY (transfer_to_ms_party_id) REFERENCES liabilities(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfer_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            transfer_document_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            measurement INTEGER NOT NULL,
            quantity REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (transfer_document_id) REFERENCES transfer_documents(id) ON DELETE CASCADE
        )
    """)

    # ---- Outward documents ----

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outward_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            outward_number TEXT UNIQUE NOT NULL,
            gp_number TEXT NOT NULL,
            sr_number TEXT,
            ms_party_id INTEGER NOT NULL,
            from_party TEXT,
            outward_to TEXT,
            vehicle_number TEXT,
            driver_name TEXT,
            total_quantity REAL DEFAULT 0.0,
            document_date TEXT NOT NULL,
            created_by TEXT NOT NULL,
            edited_by TEXT,
            edit_log_history TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ms_party_id) REFERENCES liabilities(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outward_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            outward_document_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            measurement INTEGER NOT NULL,
            quantity REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (outward_document_id) REFERENCES outward_documents(id) ON DELETE CASCADE
        )
    """)

    # ---- Invoices ----

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            invoice_number TEXT UNIQUE NOT NULL,
            ms_party_id INTEGER NOT NULL,
            number_of_items INTEGER DEFAULT 0,
            discount_amount REAL DEFAULT 0.0,
            discount_source TEXT DEFAULT 'auto',
            total_amount REAL DEFAULT 0.0,
            invoice_date TEXT NOT NULL,
            created_by TEXT NOT NULL,
            edited_by TEXT,
            edit_log_history TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ms_party_id) REFERENCES liabilities(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            invoice_id INTEGER NOT NULL,
            outward_document_id INTEGER,
            transfer_document_id INTEGER,
            item_name TEXT NOT NULL,
            measurement INTEGER NOT NULL,
            quantity REAL DEFAULT 0.0,
            rate REAL DEFAULT 0.0,
            amount REAL DEFAULT 0.0,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
            FOREIGN KEY (outward_document_id) REFERENCES outward_documents(id),
            FOREIGN KEY (transfer_document_id) REFERENCES transfer_documents(id)
        )
    """)

    # ---- Vouchers ----

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voucher_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            voucher_no TEXT UNIQUE NOT NULL,
            voucher_type TEXT NOT NULL,
            voucher_date TEXT NOT NULL,
            description TEXT,
            total_amount REAL DEFAULT 0.0,
            created_by TEXT,
            edited_by TEXT,
            edit_log_history TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voucher_detail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            voucher_id INTEGER NOT NULL,
            party_id INTEGER,
            asset_id INTEGER,
            expense_id INTEGER,
            vendor_id INTEGER,
            debit_amount REAL,
            credit_amount REAL,
            FOREIGN KEY (voucher_id) REFERENCES voucher_master(id) ON DELETE CASCADE,
            FOREIGN KEY (party_id) REFERENCES liabilities(id),
            FOREIGN KEY (asset_id) REFERENCES assets(id),
            FOREIGN KEY (expense_id) REFERENCES expenses(id),
            FOREIGN KEY (vendor_id) REFERENCES vendors(id)
        )
    """)

    # ---- Sync queue ----

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_uuid TEXT NOT NULL,
            table_name TEXT NOT NULL,
            operation_type TEXT NOT NULL,
            payload TEXT,
            sync_status INTEGER DEFAULT 0,
            retry_count INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---- Indices for sync_queue ----
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sync_queue_status
        ON sync_queue (sync_status)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sync_queue_table
        ON sync_queue (table_name)
    """)

    conn.commit()
    print(f"[LocalDB] Database initialised at {DB_PATH}")


# ---------------------------------------------------------------------------
# Sync queue helpers
# ---------------------------------------------------------------------------

def enqueue_sync(table_name: str, record_uuid: str, operation: str, payload: dict):
    """
    Add a record to the sync queue.

    Args:
        table_name: Name of the affected table.
        record_uuid: UUID of the record.
        operation: 'INSERT', 'UPDATE', or 'DELETE'.
        payload: Full row data as a dict (JSON-serializable).
    """
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO sync_queue (record_uuid, table_name, operation_type, payload)
        VALUES (?, ?, ?, ?)
        """,
        (record_uuid, table_name, operation, json.dumps(payload, default=str)),
    )
    conn.commit()


def get_pending_sync_records(limit: int = 100):
    """Return pending (unsyced) records ordered by creation time."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, record_uuid, table_name, operation_type, payload,
               retry_count, created_at
        FROM sync_queue
        WHERE sync_status = 0
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def mark_synced(sync_id: int):
    """Mark a sync-queue record as successfully synced."""
    conn = get_connection()
    conn.execute(
        "UPDATE sync_queue SET sync_status = 1 WHERE id = ?",
        (sync_id,),
    )
    conn.commit()


def mark_sync_error(sync_id: int, error_message: str):
    """Increment retry count and record the error."""
    conn = get_connection()
    conn.execute(
        """
        UPDATE sync_queue
        SET retry_count = retry_count + 1,
            error_message = ?
        WHERE id = ?
        """,
        (error_message, sync_id),
    )
    conn.commit()


def get_sync_queue_count() -> int:
    """Return the number of unsynced records."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) FROM sync_queue WHERE sync_status = 0"
    ).fetchone()
    return row[0] if row else 0


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def save_session(user_id: int, username: str, role: str, token: str, modules: list):
    """Store login session data (replaces previous session)."""
    conn = get_connection()
    conn.execute("DELETE FROM session")
    conn.execute(
        """
        INSERT INTO session (user_id, username, role, token, modules)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, username, role, token, json.dumps(modules)),
    )
    conn.commit()


def get_session() -> Optional[dict]:
    """Return the stored session, or None."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM session ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        data = dict(row)
        data["modules"] = json.loads(data.get("modules") or "[]")
        return data
    return None


# ---------------------------------------------------------------------------
# Reference-data seeding (called after successful login)
# ---------------------------------------------------------------------------

def seed_liabilities(parties: list):
    """Replace local liabilities with server data."""
    conn = get_connection()
    conn.execute("DELETE FROM liabilities")
    for p in parties:
        conn.execute(
            """
            INSERT OR REPLACE INTO liabilities
                (id, uuid, name, rate_15_yards, rate_22_yards, discount_percent,
                 is_active, is_ms_party, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p.get("id"),
                p.get("uuid", generate_uuid()),
                p.get("name"),
                p.get("rate_15_yards", 0),
                p.get("rate_22_yards", 0),
                p.get("discount_percent", 0),
                1 if p.get("is_active", True) else 0,
                1 if p.get("is_ms_party", False) else 0,
                p.get("created_at"),
                p.get("updated_at"),
            ),
        )
    conn.commit()


def seed_simple_master(table_name: str, records: list):
    """
    Replace local rows for a simple name-only master table
    (assets, expenses, vendors).
    """
    conn = get_connection()
    conn.execute(f"DELETE FROM {table_name}")
    for r in records:
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {table_name}
                (id, uuid, name, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                r.get("id"),
                r.get("uuid", generate_uuid()),
                r.get("name"),
                1 if r.get("is_active", True) else 0,
                r.get("created_at"),
                r.get("updated_at"),
            ),
        )
    conn.commit()


def seed_items(items_list: list):
    """Replace local items with server data."""
    conn = get_connection()
    conn.execute("DELETE FROM items")
    for item in items_list:
        if isinstance(item, str):
            conn.execute(
                "INSERT OR IGNORE INTO items (name) VALUES (?)", (item,)
            )
        else:
            conn.execute(
                "INSERT OR REPLACE INTO items (id, name) VALUES (?, ?)",
                (item.get("id"), item.get("name")),
            )
    conn.commit()


# ---------------------------------------------------------------------------
# Auto-numbering
# ---------------------------------------------------------------------------

def get_next_number(counter_type: str, party_name: str = None) -> int:
    """
    Atomically increment and return the next counter value.
    Used for inward_number, transfer_number, etc.
    """
    conn = get_connection()
    key = party_name or "__global__"
    row = conn.execute(
        "SELECT counter_value FROM auto_numbering WHERE counter_type = ? AND party_name = ?",
        (counter_type, key),
    ).fetchone()

    if row:
        new_val = row[0] + 1
        conn.execute(
            "UPDATE auto_numbering SET counter_value = ? WHERE counter_type = ? AND party_name = ?",
            (new_val, counter_type, key),
        )
    else:
        new_val = 1
        conn.execute(
            "INSERT INTO auto_numbering (counter_type, counter_value, party_name) VALUES (?, ?, ?)",
            (counter_type, new_val, key),
        )
    conn.commit()
    return new_val
