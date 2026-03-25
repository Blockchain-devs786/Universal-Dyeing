"""
Sync Endpoints for TMS Host Server

Receives batched offline changes from clients via POST /api/sync/push.
Each record is identified by a UUID to prevent duplicates.

Processing logic:
  - INSERT: If UUID already exists in the target table → skip (duplicate)
  - UPDATE: Find row by UUID and update its columns
  - DELETE: Find row by UUID and delete it

After processing transactional records the server can recalculate stock.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import traceback

from host.db_pool import db_pool

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SyncRecord(BaseModel):
    uuid: str
    table_name: str
    operation_type: str  # INSERT | UPDATE | DELETE
    data: Dict[str, Any]


class SyncPushRequest(BaseModel):
    records: List[SyncRecord]


class SyncRecordResult(BaseModel):
    uuid: str
    table_name: str
    operation_type: str
    success: bool
    error: Optional[str] = None


class SyncPushResponse(BaseModel):
    success: bool
    results: List[SyncRecordResult]
    synced: int
    failed: int


# ---------------------------------------------------------------------------
# Column allow-lists per table (prevents SQL injection)
# ---------------------------------------------------------------------------

ALLOWED_COLUMNS = {
    "liabilities": [
        "name", "rate_15_yards", "rate_22_yards", "discount_percent",
        "is_ms_party", "is_active", "uuid",
    ],
    "inward_documents": [
        "inward_number", "gp_number", "sr_number", "ms_party_id",
        "from_party", "vehicle_number", "driver_name", "total_quantity",
        "document_date", "created_by", "edited_by", "edit_log_history", "uuid",
    ],
    "inward_items": [
        "inward_document_id", "item_name", "measurement", "quantity", "uuid",
    ],
    "transfer_documents": [
        "transfer_number", "gp_number", "sr_number", "ms_party_id",
        "from_party", "transfer_to", "transfer_to_ms_party_id",
        "vehicle_number", "driver_name", "total_quantity", "transfer_type",
        "document_date", "created_by", "edited_by", "edit_log_history", "uuid",
    ],
    "transfer_items": [
        "transfer_document_id", "item_name", "measurement", "quantity", "uuid",
    ],
    "outward_documents": [
        "outward_number", "gp_number", "sr_number", "ms_party_id",
        "from_party", "outward_to", "vehicle_number", "driver_name",
        "total_quantity", "document_date", "created_by", "edited_by",
        "edit_log_history", "uuid",
    ],
    "outward_items": [
        "outward_document_id", "item_name", "measurement", "quantity", "uuid",
    ],
    "invoices": [
        "invoice_number", "ms_party_id", "number_of_items",
        "discount_amount", "discount_source", "total_amount",
        "invoice_date", "created_by", "edited_by", "edit_log_history", "uuid",
    ],
    "invoice_items": [
        "invoice_id", "outward_document_id", "transfer_document_id",
        "item_name", "measurement", "quantity", "rate", "amount", "uuid",
    ],
    "voucher_master": [
        "voucher_no", "voucher_type", "voucher_date", "description",
        "total_amount", "created_by", "edited_by", "edit_log_history", "uuid",
    ],
    "voucher_detail": [
        "voucher_id", "party_id", "asset_id", "expense_id", "vendor_id",
        "debit_amount", "credit_amount", "uuid",
    ],
}

# Tables that are valid sync targets
SYNCABLE_TABLES = set(ALLOWED_COLUMNS.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_insert(table: str, data: dict, uuid_val: str):
    """Build a parameterised INSERT statement from whitelisted columns."""
    allowed = ALLOWED_COLUMNS.get(table, [])
    cols = []
    vals = []
    placeholders = []

    # Always include uuid
    cols.append("uuid")
    vals.append(uuid_val)
    placeholders.append("%s")

    for col in allowed:
        if col == "uuid":
            continue  # already added
        if col in data:
            cols.append(col)
            vals.append(data[col])
            placeholders.append("%s")

    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
    return sql, vals


def _build_update(table: str, data: dict, uuid_val: str):
    """Build a parameterised UPDATE ... WHERE uuid = ? statement."""
    allowed = ALLOWED_COLUMNS.get(table, [])
    sets = []
    vals = []

    for col in allowed:
        if col == "uuid":
            continue
        if col in data:
            sets.append(f"{col} = %s")
            vals.append(data[col])

    if not sets:
        return None, None

    vals.append(uuid_val)
    sql = f"UPDATE {table} SET {', '.join(sets)} WHERE uuid = %s"
    return sql, vals


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/api/sync/push")
async def sync_push(req: SyncPushRequest):
    """
    Receive a batch of offline changes and apply them to the MySQL database.
    Returns per-record success/failure.
    """
    results: List[SyncRecordResult] = []
    synced = 0
    failed = 0

    conn = None
    cursor = None
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        for rec in req.records:
            res = _process_record(cursor, conn, rec)
            results.append(res)
            if res.success:
                synced += 1
            else:
                failed += 1

        # Commit any remaining uncommitted work
        try:
            conn.commit()
        except Exception:
            pass

    except Exception as e:
        traceback.print_exc()
        # If we have't processed anything yet, return a global error
        if not results:
            return SyncPushResponse(
                success=False,
                results=[],
                synced=0,
                failed=len(req.records),
            )
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                db_pool.return_connection(conn)
            except Exception:
                pass

    return SyncPushResponse(
        success=failed == 0,
        results=results,
        synced=synced,
        failed=failed,
    )


def _process_record(cursor, conn, rec: SyncRecord) -> SyncRecordResult:
    """Process a single sync record inside the provided cursor."""
    table = rec.table_name
    op = rec.operation_type.upper()
    uuid_val = rec.uuid
    data = rec.data or {}

    # Validate table
    if table not in SYNCABLE_TABLES:
        return SyncRecordResult(
            uuid=uuid_val, table_name=table, operation_type=op,
            success=False, error=f"Table '{table}' is not syncable",
        )

    try:
        if op == "INSERT":
            return _handle_insert(cursor, conn, table, uuid_val, data)
        elif op == "UPDATE":
            return _handle_update(cursor, conn, table, uuid_val, data)
        elif op == "DELETE":
            return _handle_delete(cursor, conn, table, uuid_val)
        else:
            return SyncRecordResult(
                uuid=uuid_val, table_name=table, operation_type=op,
                success=False, error=f"Unknown operation '{op}'",
            )
    except Exception as e:
        traceback.print_exc()
        try:
            conn.rollback()
        except Exception:
            pass
        return SyncRecordResult(
            uuid=uuid_val, table_name=table, operation_type=op,
            success=False, error=str(e),
        )


def _handle_insert(cursor, conn, table, uuid_val, data) -> SyncRecordResult:
    """INSERT — skip if UUID already exists (duplicate prevention)."""
    # Check for existing UUID
    cursor.execute(f"SELECT id FROM {table} WHERE uuid = %s", (uuid_val,))
    existing = cursor.fetchone()
    if existing:
        # Already synced — treat as success (idempotent)
        return SyncRecordResult(
            uuid=uuid_val, table_name=table, operation_type="INSERT",
            success=True, error=None,
        )

    # Resolve foreign key references that use local IDs
    # The client stores local SQLite IDs; we need to map them to server IDs via UUID
    _resolve_parent_ids(cursor, table, data)

    sql, vals = _build_insert(table, data, uuid_val)
    cursor.execute(sql, vals)
    conn.commit()

    # If this was a parent record (e.g. inward_documents), store the mapping
    # so child records can reference the server-side ID
    return SyncRecordResult(
        uuid=uuid_val, table_name=table, operation_type="INSERT",
        success=True, error=None,
    )


def _handle_update(cursor, conn, table, uuid_val, data) -> SyncRecordResult:
    """UPDATE — find by UUID and update. Last-write-wins."""
    cursor.execute(f"SELECT id FROM {table} WHERE uuid = %s", (uuid_val,))
    existing = cursor.fetchone()
    if not existing:
        # Record doesn't exist — try inserting instead
        return _handle_insert(cursor, conn, table, uuid_val, data)

    _resolve_parent_ids(cursor, table, data)

    sql, vals = _build_update(table, data, uuid_val)
    if sql:
        cursor.execute(sql, vals)
        conn.commit()

    return SyncRecordResult(
        uuid=uuid_val, table_name=table, operation_type="UPDATE",
        success=True, error=None,
    )


def _handle_delete(cursor, conn, table, uuid_val) -> SyncRecordResult:
    """DELETE — find by UUID and delete."""
    cursor.execute(f"SELECT id FROM {table} WHERE uuid = %s", (uuid_val,))
    existing = cursor.fetchone()
    if not existing:
        # Already gone — treat as success
        return SyncRecordResult(
            uuid=uuid_val, table_name=table, operation_type="DELETE",
            success=True, error=None,
        )

    cursor.execute(f"DELETE FROM {table} WHERE uuid = %s", (uuid_val,))
    conn.commit()

    return SyncRecordResult(
        uuid=uuid_val, table_name=table, operation_type="DELETE",
        success=True, error=None,
    )


# ---------------------------------------------------------------------------
# Foreign key resolution
# ---------------------------------------------------------------------------

# Mapping: (child_table, fk_column) → parent_table
FK_MAPPINGS = {
    ("inward_items", "inward_document_id"): "inward_documents",
    ("transfer_items", "transfer_document_id"): "transfer_documents",
    ("outward_items", "outward_document_id"): "outward_documents",
    ("invoice_items", "invoice_id"): "invoices",
    ("invoice_items", "outward_document_id"): "outward_documents",
    ("invoice_items", "transfer_document_id"): "transfer_documents",
    ("voucher_detail", "voucher_id"): "voucher_master",
}


def _resolve_parent_ids(cursor, table: str, data: dict):
    """
    If the data contains a `_parent_uuid_<fk_col>` key, look up the parent
    record's server-side ID by UUID and replace the FK value in `data`.
    
    The client sync engine should include `_parent_uuid_<fk_col>` fields
    when the FK references a record that was also created offline.
    """
    keys_to_remove = []
    updates = {}

    for key in list(data.keys()):
        if key.startswith("_parent_uuid_"):
            fk_col = key[len("_parent_uuid_"):]
            parent_uuid = data[key]
            parent_table_key = (table, fk_col)
            parent_table = FK_MAPPINGS.get(parent_table_key)

            if parent_table and parent_uuid:
                cursor.execute(
                    f"SELECT id FROM {parent_table} WHERE uuid = %s",
                    (parent_uuid,),
                )
                row = cursor.fetchone()
                if row:
                    updates[fk_col] = row["id"]

            keys_to_remove.append(key)

    # Apply updates and remove helper keys
    for k in keys_to_remove:
        del data[k]
    data.update(updates)
