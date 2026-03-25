"""
Local Data Service — offline CRUD layer for TMS Client

Provides the same dict-based response structure that the UI modules currently
receive from APIClient, but all reads/writes go to the local SQLite database.
Every mutating operation also enqueues a sync_queue entry.
"""

import json
from datetime import datetime
from typing import Optional, Dict, List, Any

from client.local_db import (
    get_connection,
    generate_uuid,
    enqueue_sync,
    get_next_number as _next_number,
)


class LocalDataService:
    """
    Drop-in replacement for APIClient for offline data operations.
    All methods return dicts matching the existing API response format
    so that the UI layer needs minimal changes.
    """

    def __init__(self, username: str = "offline_user"):
        self.username = username

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rows_to_dicts(rows) -> list:
        """Convert sqlite3.Row objects to plain dicts."""
        return [dict(r) for r in rows]

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    # Parties (liabilities)
    # ------------------------------------------------------------------

    def get_parties(self) -> dict:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM liabilities ORDER BY name"
        ).fetchall()
        return {"success": True, "parties": self._rows_to_dicts(rows)}

    def create_party(self, data: dict) -> dict:
        conn = get_connection()
        uid = generate_uuid()
        now = self._now()
        conn.execute(
            """
            INSERT INTO liabilities
                (uuid, name, rate_15_yards, rate_22_yards, discount_percent,
                 is_active, is_ms_party, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uid,
                data.get("name"),
                data.get("rate_15_yards", 0),
                data.get("rate_22_yards", 0),
                data.get("discount_percent", 0),
                1 if data.get("is_active", True) else 0,
                1 if data.get("is_ms_party", False) else 0,
                now,
                now,
            ),
        )
        party_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        enqueue_sync("liabilities", uid, "INSERT", {**data, "id": party_id, "uuid": uid})
        return {"success": True, "party_id": party_id, "uuid": uid}

    def update_party(self, party_id: int, data: dict) -> dict:
        conn = get_connection()
        row = conn.execute("SELECT uuid FROM liabilities WHERE id = ?", (party_id,)).fetchone()
        uid = row["uuid"] if row else generate_uuid()
        now = self._now()
        conn.execute(
            """
            UPDATE liabilities
            SET name = ?, rate_15_yards = ?, rate_22_yards = ?,
                discount_percent = ?, is_active = ?, is_ms_party = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                data.get("name"),
                data.get("rate_15_yards", 0),
                data.get("rate_22_yards", 0),
                data.get("discount_percent", 0),
                1 if data.get("is_active", True) else 0,
                1 if data.get("is_ms_party", False) else 0,
                now,
                party_id,
            ),
        )
        conn.commit()
        enqueue_sync("liabilities", uid, "UPDATE", {**data, "id": party_id, "uuid": uid})
        return {"success": True}

    def delete_party(self, party_id: int) -> dict:
        conn = get_connection()
        row = conn.execute("SELECT uuid FROM liabilities WHERE id = ?", (party_id,)).fetchone()
        uid = row["uuid"] if row else ""
        conn.execute("DELETE FROM liabilities WHERE id = ?", (party_id,))
        conn.commit()
        if uid:
            enqueue_sync("liabilities", uid, "DELETE", {"id": party_id, "uuid": uid})
        return {"success": True}

    # ------------------------------------------------------------------
    # Assets / Expenses / Vendors (read from seeded master tables)
    # ------------------------------------------------------------------

    def get_assets(self) -> dict:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM assets ORDER BY name").fetchall()
        return {"success": True, "assets": self._rows_to_dicts(rows)}

    def get_expenses(self) -> dict:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM expenses ORDER BY name").fetchall()
        return {"success": True, "expenses": self._rows_to_dicts(rows)}

    def get_vendors(self) -> dict:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM vendors ORDER BY name").fetchall()
        return {"success": True, "vendors": self._rows_to_dicts(rows)}

    # ------------------------------------------------------------------
    # Inward documents
    # ------------------------------------------------------------------

    def get_inward_documents(self) -> dict:
        conn = get_connection()
        docs = conn.execute("""
            SELECT d.*, l.name AS ms_party_name
            FROM inward_documents d
            LEFT JOIN liabilities l ON d.ms_party_id = l.id
            ORDER BY d.document_date DESC, d.id DESC
        """).fetchall()
        result = []
        for doc in docs:
            d = dict(doc)
            items = conn.execute(
                "SELECT * FROM inward_items WHERE inward_document_id = ?",
                (d["id"],),
            ).fetchall()
            d["items"] = self._rows_to_dicts(items)
            result.append(d)
        return {"success": True, "documents": result}

    def get_inward_document(self, doc_id: int) -> dict:
        conn = get_connection()
        doc = conn.execute("""
            SELECT d.*, l.name AS ms_party_name
            FROM inward_documents d
            LEFT JOIN liabilities l ON d.ms_party_id = l.id
            WHERE d.id = ?
        """, (doc_id,)).fetchone()
        if not doc:
            return {"success": False, "message": "Document not found"}
        d = dict(doc)
        items = conn.execute(
            "SELECT * FROM inward_items WHERE inward_document_id = ?",
            (d["id"],),
        ).fetchall()
        d["items"] = self._rows_to_dicts(items)
        return {"success": True, "document": d}

    def create_inward(self, data: dict) -> dict:
        conn = get_connection()
        doc_uuid = generate_uuid()
        now = self._now()

        # Auto-generate inward number
        party_name = data.get("ms_party_name", "")
        counter = _next_number("inward", party_name)
        prefix = party_name[:3].upper() if party_name else "INW"
        inward_number = data.get("inward_number") or f"{prefix}-{counter:04d}"

        total_qty = sum(
            item.get("quantity", 0) for item in data.get("items", [])
        )

        conn.execute(
            """
            INSERT INTO inward_documents
                (uuid, inward_number, gp_number, sr_number, ms_party_id,
                 from_party, vehicle_number, driver_name, total_quantity,
                 document_date, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_uuid,
                inward_number,
                data.get("gp_number", ""),
                data.get("sr_number"),
                data.get("ms_party_id"),
                data.get("from_party"),
                data.get("vehicle_number"),
                data.get("driver_name"),
                total_qty,
                data.get("document_date", datetime.now().strftime("%Y-%m-%d")),
                self.username,
                now,
                now,
            ),
        )
        doc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Insert items
        item_payloads = []
        for item in data.get("items", []):
            item_uuid = generate_uuid()
            conn.execute(
                """
                INSERT INTO inward_items
                    (uuid, inward_document_id, item_name, measurement, quantity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    item_uuid,
                    doc_id,
                    item.get("item_name"),
                    item.get("measurement"),
                    item.get("quantity", 0),
                ),
            )
            item_payloads.append({**item, "uuid": item_uuid})

        conn.commit()
        enqueue_sync("inward_documents", doc_uuid, "INSERT", {
            **data, "id": doc_id, "uuid": doc_uuid,
            "inward_number": inward_number,
            "items": item_payloads,
        })

        # Return the saved document for optimistic UI update
        saved = self.get_inward_document(doc_id)
        return {
            "success": True,
            "document_id": doc_id,
            "document": saved.get("document", {}),
        }

    def update_inward(self, doc_id: int, data: dict) -> dict:
        conn = get_connection()
        row = conn.execute(
            "SELECT uuid FROM inward_documents WHERE id = ?", (doc_id,)
        ).fetchone()
        doc_uuid = row["uuid"] if row else generate_uuid()
        now = self._now()

        total_qty = sum(
            item.get("quantity", 0) for item in data.get("items", [])
        )

        edit_log = json.dumps({
            "edited_by": self.username,
            "edited_at": now,
        })

        conn.execute(
            """
            UPDATE inward_documents
            SET gp_number = ?, sr_number = ?, ms_party_id = ?,
                from_party = ?, vehicle_number = ?, driver_name = ?,
                total_quantity = ?, document_date = ?,
                edited_by = ?, edit_log_history = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                data.get("gp_number", ""),
                data.get("sr_number"),
                data.get("ms_party_id"),
                data.get("from_party"),
                data.get("vehicle_number"),
                data.get("driver_name"),
                total_qty,
                data.get("document_date"),
                self.username,
                edit_log,
                now,
                doc_id,
            ),
        )

        # Replace items
        conn.execute("DELETE FROM inward_items WHERE inward_document_id = ?", (doc_id,))
        item_payloads = []
        for item in data.get("items", []):
            item_uuid = generate_uuid()
            conn.execute(
                """
                INSERT INTO inward_items
                    (uuid, inward_document_id, item_name, measurement, quantity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    item_uuid,
                    doc_id,
                    item.get("item_name"),
                    item.get("measurement"),
                    item.get("quantity", 0),
                ),
            )
            item_payloads.append({**item, "uuid": item_uuid})

        conn.commit()
        enqueue_sync("inward_documents", doc_uuid, "UPDATE", {
            **data, "id": doc_id, "uuid": doc_uuid, "items": item_payloads,
        })

        saved = self.get_inward_document(doc_id)
        return {
            "success": True,
            "document": saved.get("document", {}),
        }

    def delete_inward(self, doc_id: int) -> dict:
        conn = get_connection()
        row = conn.execute(
            "SELECT uuid FROM inward_documents WHERE id = ?", (doc_id,)
        ).fetchone()
        doc_uuid = row["uuid"] if row else ""
        conn.execute("DELETE FROM inward_documents WHERE id = ?", (doc_id,))
        conn.commit()
        if doc_uuid:
            enqueue_sync("inward_documents", doc_uuid, "DELETE", {
                "id": doc_id, "uuid": doc_uuid,
            })
        return {"success": True}

    # ------------------------------------------------------------------
    # Transfer documents
    # ------------------------------------------------------------------

    def get_transfer_documents(self) -> dict:
        conn = get_connection()
        docs = conn.execute("""
            SELECT d.*, l.name AS ms_party_name,
                   l2.name AS transfer_to_ms_party_name
            FROM transfer_documents d
            LEFT JOIN liabilities l ON d.ms_party_id = l.id
            LEFT JOIN liabilities l2 ON d.transfer_to_ms_party_id = l2.id
            ORDER BY d.document_date DESC, d.id DESC
        """).fetchall()
        result = []
        for doc in docs:
            d = dict(doc)
            items = conn.execute(
                "SELECT * FROM transfer_items WHERE transfer_document_id = ?",
                (d["id"],),
            ).fetchall()
            d["items"] = self._rows_to_dicts(items)
            result.append(d)
        return {"success": True, "documents": result}

    def create_transfer(self, data: dict) -> dict:
        conn = get_connection()
        doc_uuid = generate_uuid()
        now = self._now()
        party_name = data.get("ms_party_name", "")
        counter = _next_number("transfer", party_name)
        prefix = party_name[:3].upper() if party_name else "TRF"
        transfer_number = data.get("transfer_number") or f"{prefix}-T{counter:04d}"

        total_qty = sum(item.get("quantity", 0) for item in data.get("items", []))

        conn.execute(
            """
            INSERT INTO transfer_documents
                (uuid, transfer_number, gp_number, sr_number, ms_party_id,
                 from_party, transfer_to, transfer_to_ms_party_id,
                 vehicle_number, driver_name, total_quantity,
                 transfer_type, document_date, created_by,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_uuid,
                transfer_number,
                data.get("gp_number", ""),
                data.get("sr_number"),
                data.get("ms_party_id"),
                data.get("from_party"),
                data.get("transfer_to"),
                data.get("transfer_to_ms_party_id"),
                data.get("vehicle_number"),
                data.get("driver_name"),
                total_qty,
                data.get("transfer_type", "simple"),
                data.get("document_date", datetime.now().strftime("%Y-%m-%d")),
                self.username,
                now,
                now,
            ),
        )
        doc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        item_payloads = []
        for item in data.get("items", []):
            item_uuid = generate_uuid()
            conn.execute(
                """
                INSERT INTO transfer_items
                    (uuid, transfer_document_id, item_name, measurement, quantity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item_uuid, doc_id, item.get("item_name"),
                 item.get("measurement"), item.get("quantity", 0)),
            )
            item_payloads.append({**item, "uuid": item_uuid})

        conn.commit()
        enqueue_sync("transfer_documents", doc_uuid, "INSERT", {
            **data, "id": doc_id, "uuid": doc_uuid,
            "transfer_number": transfer_number, "items": item_payloads,
        })
        return {"success": True, "document_id": doc_id, "transfer_number": transfer_number}

    def update_transfer(self, doc_id: int, data: dict) -> dict:
        conn = get_connection()
        row = conn.execute(
            "SELECT uuid FROM transfer_documents WHERE id = ?", (doc_id,)
        ).fetchone()
        doc_uuid = row["uuid"] if row else generate_uuid()
        now = self._now()
        total_qty = sum(item.get("quantity", 0) for item in data.get("items", []))
        edit_log = json.dumps({"edited_by": self.username, "edited_at": now})

        conn.execute(
            """
            UPDATE transfer_documents
            SET gp_number = ?, sr_number = ?, ms_party_id = ?,
                from_party = ?, transfer_to = ?, transfer_to_ms_party_id = ?,
                vehicle_number = ?, driver_name = ?, total_quantity = ?,
                transfer_type = ?, document_date = ?,
                edited_by = ?, edit_log_history = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                data.get("gp_number", ""), data.get("sr_number"),
                data.get("ms_party_id"), data.get("from_party"),
                data.get("transfer_to"), data.get("transfer_to_ms_party_id"),
                data.get("vehicle_number"), data.get("driver_name"),
                total_qty, data.get("transfer_type", "simple"),
                data.get("document_date"), self.username, edit_log, now,
                doc_id,
            ),
        )

        conn.execute("DELETE FROM transfer_items WHERE transfer_document_id = ?", (doc_id,))
        item_payloads = []
        for item in data.get("items", []):
            item_uuid = generate_uuid()
            conn.execute(
                """
                INSERT INTO transfer_items
                    (uuid, transfer_document_id, item_name, measurement, quantity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item_uuid, doc_id, item.get("item_name"),
                 item.get("measurement"), item.get("quantity", 0)),
            )
            item_payloads.append({**item, "uuid": item_uuid})

        conn.commit()
        enqueue_sync("transfer_documents", doc_uuid, "UPDATE", {
            **data, "id": doc_id, "uuid": doc_uuid, "items": item_payloads,
        })
        return {"success": True}

    def delete_transfer(self, doc_id: int) -> dict:
        conn = get_connection()
        row = conn.execute(
            "SELECT uuid FROM transfer_documents WHERE id = ?", (doc_id,)
        ).fetchone()
        doc_uuid = row["uuid"] if row else ""
        conn.execute("DELETE FROM transfer_documents WHERE id = ?", (doc_id,))
        conn.commit()
        if doc_uuid:
            enqueue_sync("transfer_documents", doc_uuid, "DELETE", {
                "id": doc_id, "uuid": doc_uuid,
            })
        return {"success": True}

    # ------------------------------------------------------------------
    # Outward documents
    # ------------------------------------------------------------------

    def get_outward_documents(self) -> dict:
        conn = get_connection()
        docs = conn.execute("""
            SELECT d.*, l.name AS ms_party_name
            FROM outward_documents d
            LEFT JOIN liabilities l ON d.ms_party_id = l.id
            ORDER BY d.document_date DESC, d.id DESC
        """).fetchall()
        result = []
        for doc in docs:
            d = dict(doc)
            items = conn.execute(
                "SELECT * FROM outward_items WHERE outward_document_id = ?",
                (d["id"],),
            ).fetchall()
            d["items"] = self._rows_to_dicts(items)
            result.append(d)
        return {"success": True, "documents": result}

    def create_outward(self, data: dict) -> dict:
        conn = get_connection()
        doc_uuid = generate_uuid()
        now = self._now()
        party_name = data.get("ms_party_name", "")
        counter = _next_number("outward", party_name)
        prefix = party_name[:3].upper() if party_name else "OUT"
        outward_number = data.get("outward_number") or f"{prefix}-O{counter:04d}"

        total_qty = sum(item.get("quantity", 0) for item in data.get("items", []))

        conn.execute(
            """
            INSERT INTO outward_documents
                (uuid, outward_number, gp_number, sr_number, ms_party_id,
                 from_party, outward_to, vehicle_number, driver_name,
                 total_quantity, document_date, created_by,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_uuid, outward_number,
                data.get("gp_number", ""), data.get("sr_number"),
                data.get("ms_party_id"), data.get("from_party"),
                data.get("outward_to"), data.get("vehicle_number"),
                data.get("driver_name"), total_qty,
                data.get("document_date", datetime.now().strftime("%Y-%m-%d")),
                self.username, now, now,
            ),
        )
        doc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        item_payloads = []
        for item in data.get("items", []):
            item_uuid = generate_uuid()
            conn.execute(
                """
                INSERT INTO outward_items
                    (uuid, outward_document_id, item_name, measurement, quantity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item_uuid, doc_id, item.get("item_name"),
                 item.get("measurement"), item.get("quantity", 0)),
            )
            item_payloads.append({**item, "uuid": item_uuid})

        conn.commit()
        enqueue_sync("outward_documents", doc_uuid, "INSERT", {
            **data, "id": doc_id, "uuid": doc_uuid,
            "outward_number": outward_number, "items": item_payloads,
        })
        return {"success": True, "document_id": doc_id, "outward_number": outward_number}

    def update_outward(self, doc_id: int, data: dict) -> dict:
        conn = get_connection()
        row = conn.execute(
            "SELECT uuid FROM outward_documents WHERE id = ?", (doc_id,)
        ).fetchone()
        doc_uuid = row["uuid"] if row else generate_uuid()
        now = self._now()
        total_qty = sum(item.get("quantity", 0) for item in data.get("items", []))
        edit_log = json.dumps({"edited_by": self.username, "edited_at": now})

        conn.execute(
            """
            UPDATE outward_documents
            SET gp_number = ?, sr_number = ?, ms_party_id = ?,
                from_party = ?, outward_to = ?,
                vehicle_number = ?, driver_name = ?, total_quantity = ?,
                document_date = ?, edited_by = ?, edit_log_history = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                data.get("gp_number", ""), data.get("sr_number"),
                data.get("ms_party_id"), data.get("from_party"),
                data.get("outward_to"), data.get("vehicle_number"),
                data.get("driver_name"), total_qty,
                data.get("document_date"), self.username, edit_log, now,
                doc_id,
            ),
        )

        conn.execute("DELETE FROM outward_items WHERE outward_document_id = ?", (doc_id,))
        item_payloads = []
        for item in data.get("items", []):
            item_uuid = generate_uuid()
            conn.execute(
                """
                INSERT INTO outward_items
                    (uuid, outward_document_id, item_name, measurement, quantity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item_uuid, doc_id, item.get("item_name"),
                 item.get("measurement"), item.get("quantity", 0)),
            )
            item_payloads.append({**item, "uuid": item_uuid})

        conn.commit()
        enqueue_sync("outward_documents", doc_uuid, "UPDATE", {
            **data, "id": doc_id, "uuid": doc_uuid, "items": item_payloads,
        })
        return {"success": True}

    def delete_outward(self, doc_id: int) -> dict:
        conn = get_connection()
        row = conn.execute(
            "SELECT uuid FROM outward_documents WHERE id = ?", (doc_id,)
        ).fetchone()
        doc_uuid = row["uuid"] if row else ""
        conn.execute("DELETE FROM outward_documents WHERE id = ?", (doc_id,))
        conn.commit()
        if doc_uuid:
            enqueue_sync("outward_documents", doc_uuid, "DELETE", {
                "id": doc_id, "uuid": doc_uuid,
            })
        return {"success": True}

    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------

    def get_invoices(self) -> dict:
        conn = get_connection()
        docs = conn.execute("""
            SELECT i.*, l.name AS ms_party_name
            FROM invoices i
            LEFT JOIN liabilities l ON i.ms_party_id = l.id
            ORDER BY i.invoice_date DESC, i.id DESC
        """).fetchall()
        result = []
        for inv in docs:
            d = dict(inv)
            items = conn.execute(
                "SELECT * FROM invoice_items WHERE invoice_id = ?",
                (d["id"],),
            ).fetchall()
            d["items"] = self._rows_to_dicts(items)
            result.append(d)
        return {"success": True, "documents": result}

    def create_invoice(self, data: dict) -> dict:
        conn = get_connection()
        doc_uuid = generate_uuid()
        now = self._now()
        party_name = data.get("ms_party_name", "")
        counter = _next_number("invoice", party_name)
        prefix = party_name[:3].upper() if party_name else "INV"
        invoice_number = data.get("invoice_number") or f"{prefix}-I{counter:04d}"

        items_list = data.get("items", [])
        total_amount = sum(item.get("amount", 0) for item in items_list)

        conn.execute(
            """
            INSERT INTO invoices
                (uuid, invoice_number, ms_party_id, number_of_items,
                 discount_amount, discount_source, total_amount,
                 invoice_date, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_uuid, invoice_number,
                data.get("ms_party_id"), len(items_list),
                data.get("discount_amount", 0),
                data.get("discount_source", "auto"),
                total_amount,
                data.get("invoice_date", datetime.now().strftime("%Y-%m-%d")),
                self.username, now, now,
            ),
        )
        doc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        item_payloads = []
        for item in items_list:
            item_uuid = generate_uuid()
            conn.execute(
                """
                INSERT INTO invoice_items
                    (uuid, invoice_id, outward_document_id,
                     transfer_document_id, item_name, measurement,
                     quantity, rate, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_uuid, doc_id,
                    item.get("outward_document_id"),
                    item.get("transfer_document_id"),
                    item.get("item_name"),
                    item.get("measurement"),
                    item.get("quantity", 0),
                    item.get("rate", 0),
                    item.get("amount", 0),
                ),
            )
            item_payloads.append({**item, "uuid": item_uuid})

        conn.commit()
        enqueue_sync("invoices", doc_uuid, "INSERT", {
            **data, "id": doc_id, "uuid": doc_uuid,
            "invoice_number": invoice_number, "items": item_payloads,
        })
        return {"success": True, "invoice_id": doc_id, "invoice_number": invoice_number}

    def update_invoice(self, doc_id: int, data: dict) -> dict:
        conn = get_connection()
        row = conn.execute(
            "SELECT uuid FROM invoices WHERE id = ?", (doc_id,)
        ).fetchone()
        doc_uuid = row["uuid"] if row else generate_uuid()
        now = self._now()
        items_list = data.get("items", [])
        total_amount = sum(item.get("amount", 0) for item in items_list)
        edit_log = json.dumps({"edited_by": self.username, "edited_at": now})

        conn.execute(
            """
            UPDATE invoices
            SET ms_party_id = ?, number_of_items = ?,
                discount_amount = ?, discount_source = ?,
                total_amount = ?, invoice_date = ?,
                edited_by = ?, edit_log_history = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                data.get("ms_party_id"), len(items_list),
                data.get("discount_amount", 0),
                data.get("discount_source", "auto"),
                total_amount, data.get("invoice_date"),
                self.username, edit_log, now,
                doc_id,
            ),
        )

        conn.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (doc_id,))
        item_payloads = []
        for item in items_list:
            item_uuid = generate_uuid()
            conn.execute(
                """
                INSERT INTO invoice_items
                    (uuid, invoice_id, outward_document_id,
                     transfer_document_id, item_name, measurement,
                     quantity, rate, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_uuid, doc_id,
                    item.get("outward_document_id"),
                    item.get("transfer_document_id"),
                    item.get("item_name"),
                    item.get("measurement"),
                    item.get("quantity", 0),
                    item.get("rate", 0),
                    item.get("amount", 0),
                ),
            )
            item_payloads.append({**item, "uuid": item_uuid})

        conn.commit()
        enqueue_sync("invoices", doc_uuid, "UPDATE", {
            **data, "id": doc_id, "uuid": doc_uuid, "items": item_payloads,
        })
        return {"success": True}

    def delete_invoice(self, doc_id: int) -> dict:
        conn = get_connection()
        row = conn.execute(
            "SELECT uuid FROM invoices WHERE id = ?", (doc_id,)
        ).fetchone()
        doc_uuid = row["uuid"] if row else ""
        conn.execute("DELETE FROM invoices WHERE id = ?", (doc_id,))
        conn.commit()
        if doc_uuid:
            enqueue_sync("invoices", doc_uuid, "DELETE", {
                "id": doc_id, "uuid": doc_uuid,
            })
        return {"success": True}

    # ------------------------------------------------------------------
    # Vouchers
    # ------------------------------------------------------------------

    def get_vouchers(self, voucher_type: str = None) -> dict:
        conn = get_connection()
        if voucher_type:
            rows = conn.execute("""
                SELECT * FROM voucher_master
                WHERE voucher_type = ?
                ORDER BY voucher_date DESC, id DESC
            """, (voucher_type,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM voucher_master
                ORDER BY voucher_date DESC, id DESC
            """).fetchall()
        result = []
        for row in rows:
            v = dict(row)
            details = conn.execute("""
                SELECT vd.*,
                       l.name AS party_name,
                       a.name AS asset_name,
                       e.name AS expense_name,
                       vn.name AS vendor_name
                FROM voucher_detail vd
                LEFT JOIN liabilities l ON vd.party_id = l.id
                LEFT JOIN assets a ON vd.asset_id = a.id
                LEFT JOIN expenses e ON vd.expense_id = e.id
                LEFT JOIN vendors vn ON vd.vendor_id = vn.id
                WHERE vd.voucher_id = ?
            """, (v["id"],)).fetchall()
            v["details"] = self._rows_to_dicts(details)
            result.append(v)
        return {"success": True, "vouchers": result}

    def get_voucher(self, voucher_id: int) -> dict:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM voucher_master WHERE id = ?", (voucher_id,)
        ).fetchone()
        if not row:
            return {"success": False, "message": "Voucher not found"}
        v = dict(row)
        details = conn.execute("""
            SELECT vd.*,
                   l.name AS party_name,
                   a.name AS asset_name,
                   e.name AS expense_name,
                   vn.name AS vendor_name
            FROM voucher_detail vd
            LEFT JOIN liabilities l ON vd.party_id = l.id
            LEFT JOIN assets a ON vd.asset_id = a.id
            LEFT JOIN expenses e ON vd.expense_id = e.id
            LEFT JOIN vendors vn ON vd.vendor_id = vn.id
            WHERE vd.voucher_id = ?
        """, (v["id"],)).fetchall()
        v["details"] = self._rows_to_dicts(details)
        return {"success": True, "voucher": v}

    def create_voucher(self, data: dict) -> dict:
        conn = get_connection()
        v_uuid = generate_uuid()
        now = self._now()

        vtype = data.get("voucher_type", "JV")
        counter = _next_number("voucher", vtype)
        voucher_no = data.get("voucher_no") or f"{vtype}-{counter:04d}"

        details = data.get("details", [])
        total_amount = sum(d.get("debit_amount") or 0 for d in details)

        conn.execute(
            """
            INSERT INTO voucher_master
                (uuid, voucher_no, voucher_type, voucher_date,
                 description, total_amount, created_by,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                v_uuid, voucher_no, vtype,
                data.get("voucher_date", datetime.now().strftime("%Y-%m-%d")),
                data.get("description"),
                total_amount, self.username, now, now,
            ),
        )
        v_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        detail_payloads = []
        for detail in details:
            d_uuid = generate_uuid()
            conn.execute(
                """
                INSERT INTO voucher_detail
                    (uuid, voucher_id, party_id, asset_id,
                     expense_id, vendor_id, debit_amount, credit_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    d_uuid, v_id,
                    detail.get("party_id"),
                    detail.get("asset_id"),
                    detail.get("expense_id"),
                    detail.get("vendor_id"),
                    detail.get("debit_amount"),
                    detail.get("credit_amount"),
                ),
            )
            detail_payloads.append({**detail, "uuid": d_uuid})

        conn.commit()
        enqueue_sync("voucher_master", v_uuid, "INSERT", {
            **data, "id": v_id, "uuid": v_uuid,
            "voucher_no": voucher_no, "details": detail_payloads,
        })
        return {"success": True, "voucher_id": v_id, "voucher_no": voucher_no}

    def update_voucher(self, voucher_id: int, data: dict) -> dict:
        conn = get_connection()
        row = conn.execute(
            "SELECT uuid FROM voucher_master WHERE id = ?", (voucher_id,)
        ).fetchone()
        v_uuid = row["uuid"] if row else generate_uuid()
        now = self._now()

        details = data.get("details", [])
        total_amount = sum(d.get("debit_amount") or 0 for d in details)
        edit_log = json.dumps({"edited_by": self.username, "edited_at": now})

        conn.execute(
            """
            UPDATE voucher_master
            SET voucher_type = ?, voucher_date = ?,
                description = ?, total_amount = ?,
                edited_by = ?, edit_log_history = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                data.get("voucher_type"),
                data.get("voucher_date"),
                data.get("description"),
                total_amount,
                self.username,
                edit_log,
                now,
                voucher_id,
            ),
        )

        conn.execute("DELETE FROM voucher_detail WHERE voucher_id = ?", (voucher_id,))
        detail_payloads = []
        for detail in details:
            d_uuid = generate_uuid()
            conn.execute(
                """
                INSERT INTO voucher_detail
                    (uuid, voucher_id, party_id, asset_id,
                     expense_id, vendor_id, debit_amount, credit_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    d_uuid, voucher_id,
                    detail.get("party_id"),
                    detail.get("asset_id"),
                    detail.get("expense_id"),
                    detail.get("vendor_id"),
                    detail.get("debit_amount"),
                    detail.get("credit_amount"),
                ),
            )
            detail_payloads.append({**detail, "uuid": d_uuid})

        conn.commit()
        enqueue_sync("voucher_master", v_uuid, "UPDATE", {
            **data, "id": voucher_id, "uuid": v_uuid, "details": detail_payloads,
        })
        return {"success": True}

    def delete_voucher(self, voucher_id: int) -> dict:
        conn = get_connection()
        row = conn.execute(
            "SELECT uuid FROM voucher_master WHERE id = ?", (voucher_id,)
        ).fetchone()
        v_uuid = row["uuid"] if row else ""
        conn.execute("DELETE FROM voucher_master WHERE id = ?", (voucher_id,))
        conn.commit()
        if v_uuid:
            enqueue_sync("voucher_master", v_uuid, "DELETE", {
                "id": voucher_id, "uuid": v_uuid,
            })
        return {"success": True}

    def get_voucher_descriptions(self) -> dict:
        """Return distinct voucher descriptions for autocomplete."""
        conn = get_connection()
        rows = conn.execute("""
            SELECT DISTINCT description FROM voucher_master
            WHERE description IS NOT NULL AND description != ''
            ORDER BY description
        """).fetchall()
        return {
            "success": True,
            "descriptions": [r["description"] for r in rows],
        }

    # ------------------------------------------------------------------
    # Financial ledgers (read-only locally, for opening-balance check)
    # ------------------------------------------------------------------

    def get_financial_ledgers(self) -> dict:
        """Stub — opening-balance duplicate check is skipped offline."""
        return {"success": True, "ledgers": []}

    def get_financial_ledger_entries(self, ledger_id: int) -> dict:
        """Stub — opening-balance duplicate check is skipped offline."""
        return {"success": True, "entries": []}

    # ------------------------------------------------------------------
    # Stock (read-only, server calculates)
    # ------------------------------------------------------------------

    def get_stock(self, ms_party_id: int = None) -> dict:
        """
        Compute stock locally from inward - transfer - outward.
        This is a convenience read; the real stock lives on the server.
        """
        conn = get_connection()
        # Simple approach: aggregate quantities per party + item + measurement
        query = """
            SELECT ms_party_id, item_name, measurement,
                   COALESCE(SUM(quantity), 0) AS total_inward
            FROM inward_items ii
            JOIN inward_documents id2 ON ii.inward_document_id = id2.id
        """
        params = []
        if ms_party_id:
            query += " WHERE id2.ms_party_id = ?"
            params.append(ms_party_id)
        query += " GROUP BY ms_party_id, item_name, measurement"

        rows = conn.execute(query, params).fetchall()
        return {"success": True, "stock": self._rows_to_dicts(rows)}

    # ------------------------------------------------------------------
    # Items (autocomplete)
    # ------------------------------------------------------------------

    def get_items(self) -> dict:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
        return {"success": True, "items": self._rows_to_dicts(rows)}

    # ------------------------------------------------------------------
    # Auto-numbering pass-through
    # ------------------------------------------------------------------

    def get_next_number(self, counter_type: str, party_name: str = None) -> int:
        return _next_number(counter_type, party_name)
