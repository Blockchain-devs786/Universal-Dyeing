"""
Sync Engine for TMS Client (Offline-First Architecture)

Handles manual sync when user clicks "Sync Data":
1. Checks server availability via APIClient
2. Reads pending sync_queue records from local SQLite
3. Batches and sends them to POST /api/sync/push
4. Marks records as synced or increments retry_count on failure
5. Re-downloads reference data to pick up server-side changes

Sync dependency order:
  liabilities → inward_documents/items → transfer_documents/items →
  outward_documents/items → invoices/invoice_items → voucher_master/voucher_detail
"""

import json
import traceback
from PyQt5.QtCore import QThread, pyqtSignal

from client import local_db


# ---------------------------------------------------------------------------
# Dependency order: tables must be synced in this sequence
# ---------------------------------------------------------------------------
TABLE_SYNC_ORDER = [
    "liabilities",
    "inward_documents",
    "inward_items",
    "transfer_documents",
    "transfer_items",
    "outward_documents",
    "outward_items",
    "invoices",
    "invoice_items",
    "vouchers",        # mapped to voucher_master on server
    "voucher_details", # mapped to voucher_detail on server
]

# Map local table names → server table names where they differ
TABLE_NAME_MAP = {
    "vouchers": "voucher_master",
    "voucher_details": "voucher_detail",
}


class SyncWorker(QThread):
    """
    Background thread that processes the local sync queue and pushes
    records to the server via POST /api/sync/push.
    """
    # Signals
    progress = pyqtSignal(int, int, str)   # (current, total, message)
    finished = pyqtSignal(int, int, str)   # (synced_count, failed_count, summary)
    error = pyqtSignal(str)                # fatal error message

    BATCH_SIZE = 50  # records per HTTP request

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    # ------------------------------------------------------------------
    def run(self):
        try:
            self._do_sync()
        except Exception as e:
            traceback.print_exc()
            self.error.emit(f"Sync failed: {e}")

    # ------------------------------------------------------------------
    def _do_sync(self):
        # 1. Check server reachability
        self.progress.emit(0, 0, "Checking server connection…")
        if not self._ping_server():
            self.error.emit(
                "Cannot reach the server. Please ensure the host "
                "application is running and you are connected to the network."
            )
            return

        # 2. Load all pending records
        pending = local_db.get_pending_sync_records(limit=5000)
        if not pending:
            self.finished.emit(0, 0, "Nothing to sync — all data is up to date.")
            return

        total = len(pending)
        synced = 0
        failed = 0

        # 3. Sort records by table dependency order, then by created_at
        def sort_key(rec):
            tbl = rec["table_name"]
            try:
                order = TABLE_SYNC_ORDER.index(tbl)
            except ValueError:
                order = 999
            return (order, rec["created_at"])

        pending.sort(key=sort_key)

        # 4. Process in batches
        for batch_start in range(0, total, self.BATCH_SIZE):
            if self._cancelled:
                break

            batch = pending[batch_start: batch_start + self.BATCH_SIZE]
            self.progress.emit(
                batch_start, total,
                f"Syncing records {batch_start + 1}–{min(batch_start + len(batch), total)} of {total}…"
            )

            # Build request payload
            records_payload = []
            for rec in batch:
                payload = json.loads(rec["payload"]) if isinstance(rec["payload"], str) else rec["payload"]
                server_table = TABLE_NAME_MAP.get(rec["table_name"], rec["table_name"])
                records_payload.append({
                    "uuid": rec["record_uuid"],
                    "table_name": server_table,
                    "operation_type": rec["operation_type"],
                    "data": payload,
                })

            # Send to server
            try:
                response = self.api_client._try_request(
                    "POST",
                    "/api/sync/push",
                    json={"records": records_payload},
                )
                if response and response.status_code == 200:
                    result = response.json()
                    results_list = result.get("results", [])

                    for i, res in enumerate(results_list):
                        rec = batch[i] if i < len(batch) else None
                        if rec is None:
                            continue
                        if res.get("success"):
                            local_db.mark_synced(rec["id"])
                            synced += 1
                        else:
                            local_db.mark_sync_error(
                                rec["id"],
                                res.get("error", "Unknown server error"),
                            )
                            failed += 1
                else:
                    # Entire batch failed
                    err_msg = f"Server returned status {response.status_code if response else 'No response'}"
                    for rec in batch:
                        local_db.mark_sync_error(rec["id"], err_msg)
                        failed += 1
            except Exception as e:
                err_msg = str(e)
                for rec in batch:
                    local_db.mark_sync_error(rec["id"], err_msg)
                    failed += 1

        # 5. Re-download reference data
        if synced > 0:
            self.progress.emit(total, total, "Refreshing reference data…")
            self._refresh_reference_data()

        # 6. Done
        summary_parts = []
        if synced:
            summary_parts.append(f"{synced} record(s) synced successfully")
        if failed:
            summary_parts.append(f"{failed} record(s) failed")
        if not summary_parts:
            summary_parts.append("Sync completed")

        self.finished.emit(synced, failed, ". ".join(summary_parts) + ".")

    # ------------------------------------------------------------------
    def _ping_server(self) -> bool:
        """Quick connectivity test."""
        try:
            resp = self.api_client._try_request("GET", "/api/health")
            return resp is not None and resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    def _refresh_reference_data(self):
        """Re-download parties/assets/expenses/vendors from server."""
        try:
            # Parties
            resp = self.api_client._try_request("GET", "/api/parties")
            if resp and resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    local_db.seed_liabilities(data.get("parties", []))

            # Assets
            resp = self.api_client._try_request("GET", "/api/assets")
            if resp and resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    local_db.seed_simple_master("assets", data.get("assets", []))

            # Expenses
            resp = self.api_client._try_request("GET", "/api/expenses")
            if resp and resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    local_db.seed_simple_master("expenses", data.get("expenses", []))

            # Vendors
            resp = self.api_client._try_request("GET", "/api/vendors")
            if resp and resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    local_db.seed_simple_master("vendors", data.get("vendors", []))
        except Exception as e:
            print(f"[SyncEngine] Warning: Failed to refresh reference data: {e}")
