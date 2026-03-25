"""Command-Based Write APIs for Optimized High-Frequency Operations

Additive endpoints for high-frequency writes. Existing CRUD remains unchanged.
Rules:
- Single transaction per command
- Minimal delta events (versioned)
- Events are emitted only after successful commit
"""

from fastapi import HTTPException, Request
from typing import Dict, List, Tuple
from datetime import datetime
from host.db_pool import db_pool
from host.stock_manager import (
    get_next_number, update_stock_for_transfer_bn,
    get_ud_ledger_id, get_party_ledger_id, create_ledger_entry
)
from host.api_server import (
    app,
    rate_limit_check,
    get_client_ip,
    CreateInwardRequest,
    CreateTransferRequest,
    broadcast_message,
)
from host.event_system import (
    log_event,
    create_inward_delta_event,
    create_transfer_delta_event,
    create_stock_delta_event,
    EVENT_INWARD_CREATED,
    EVENT_TRANSFER_CREATED,
    EVENT_STOCK_DELTA_UPDATED,
)


# ---------- Internal helpers ----------

def _ensure_doc_date_str(value) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _update_stock_for_inward_tx(conn, ms_party_id: int, items: List[Dict], reverse: bool = False):
    """Inline the existing inward stock logic inside the provided transaction."""
    cursor = conn.cursor()
    try:
        for item in items:
            item_name = item["item_name"]
            measurement = item["measurement"]
            quantity = item["quantity"]
            if reverse:
                quantity = -quantity

            cursor.execute(
                """
                SELECT id FROM stock 
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
                """,
                (ms_party_id, item_name, measurement),
            )
            result = cursor.fetchone()

            if result:
                cursor.execute(
                    """
                    UPDATE stock SET total_inward = total_inward + %s
                    WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
                    """,
                    (quantity, ms_party_id, item_name, measurement),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO stock (ms_party_id, item_name, measurement, total_inward)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (ms_party_id, item_name, measurement, quantity),
                )
    finally:
        cursor.close()


def _update_stock_for_transfer_tx(conn, ms_party_id: int, items: List[Dict], reverse: bool = False):
    """Inline the existing simple transfer stock logic inside the provided transaction.
    
    Simple Transfer: Only deducts from source party (total_transfer), no addition to destination.
    """
    cursor = conn.cursor()
    try:
        for item in items:
            item_name = item["item_name"]
            measurement = item["measurement"]
            quantity = item["quantity"]
            if reverse:
                quantity = -quantity

            cursor.execute(
                """
                SELECT id, remaining_stock FROM stock 
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
                """,
                (ms_party_id, item_name, measurement),
            )
            result = cursor.fetchone()
            if not result:
                raise Exception(f"Stock not found for {item_name} ({measurement})")

            current_stock = float(result[1])
            if not reverse and current_stock < quantity:
                raise Exception(
                    f"Insufficient stock for {item_name} ({measurement}). Available: {current_stock}, Required: {quantity}"
                )

            # Simple transfer: only deduct from source (total_transfer)
            cursor.execute(
                """
                UPDATE stock SET total_transfer = total_transfer + %s
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
                """,
                (quantity, ms_party_id, item_name, measurement),
            )
    finally:
        cursor.close()


def _update_stock_for_transfer_bn_tx(conn, source_party_id: int, dest_party_id: int, items: List[Dict], reverse: bool = False):
    """Inline BN transfer stock logic inside the provided transaction.
    
    BN Transfer: Deducts from source (transfer_bn_out) and adds to destination (transfer_bn_in).
    """
    cursor = conn.cursor()
    try:
        for item in items:
            item_name = item["item_name"]
            measurement = item["measurement"]
            quantity = item["quantity"]
            if reverse:
                quantity = -quantity

            # Update source party stock (deduct via transfer_bn_out)
            cursor.execute(
                """
                SELECT id, remaining_stock FROM stock 
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
                """,
                (source_party_id, item_name, measurement),
            )
            source_result = cursor.fetchone()
            if not source_result:
                raise Exception(f"Stock not found for source party {source_party_id}, item {item_name} ({measurement})")

            current_stock = float(source_result[1])
            if not reverse and current_stock < quantity:
                raise Exception(
                    f"Insufficient stock for {item_name} ({measurement}). Available: {current_stock}, Required: {quantity}"
                )

            # Deduct from source (transfer_bn_out)
            cursor.execute(
                """
                UPDATE stock SET transfer_bn_out = transfer_bn_out + %s
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
                """,
                (quantity, source_party_id, item_name, measurement),
            )

            # Add to destination party (transfer_bn_in)
            cursor.execute(
                """
                SELECT id FROM stock 
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
                """,
                (dest_party_id, item_name, measurement),
            )
            dest_result = cursor.fetchone()

            if dest_result:
                # Update existing stock
                cursor.execute(
                    """
                    UPDATE stock SET transfer_bn_in = transfer_bn_in + %s
                    WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
                    """,
                    (quantity, dest_party_id, item_name, measurement),
                )
            else:
                # Create new stock record for destination (with zero inward, but BN in)
                cursor.execute(
                    """
                    INSERT INTO stock (ms_party_id, item_name, measurement, transfer_bn_in)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (dest_party_id, item_name, measurement, quantity),
                )
    finally:
        cursor.close()


def _process_inward(conn, inward_req: CreateInwardRequest) -> Dict:
    """Execute inward creation inside the given transaction and return pending events."""
    cursor = conn.cursor()

    # Validations (reuse existing rules)
    for item in inward_req.items:
        if item.measurement not in [15, 22]:
            raise HTTPException(status_code=400, detail=f"Invalid measurement: {item.measurement}. Must be 15 or 22")
    item_keys = [(item.item_name, item.measurement) for item in inward_req.items]
    if len(item_keys) != len(set(item_keys)):
        raise HTTPException(status_code=400, detail="Duplicate item + measurement combination")

    cursor.execute("SELECT name FROM liabilities WHERE id = %s", (inward_req.ms_party_id,))
    party_result = cursor.fetchone()
    if not party_result:
        raise HTTPException(status_code=404, detail="MS Party not found")
    party_name = party_result[0]

    inward_num = get_next_number("INWARD")
    if inward_num is None:
        raise HTTPException(status_code=500, detail="Failed to generate inward number")
    gp_num = inward_num
    sr_num = get_next_number("SR", party_name)
    if sr_num is None:
        raise HTTPException(status_code=500, detail="Failed to generate SR number")

    total_qty = sum(item.quantity for item in inward_req.items)

    cursor.execute(
        """
        INSERT INTO inward_documents 
        (inward_number, gp_number, sr_number, ms_party_id, from_party,
         vehicle_number, driver_name, total_quantity, document_date, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            f"IN-{inward_num:06d}",
            f"GP-{gp_num:06d}",
            f"SR-{sr_num:06d}",
            inward_req.ms_party_id,
            inward_req.from_party,
            inward_req.vehicle_number,
            inward_req.driver_name,
            total_qty,
            inward_req.document_date,
            inward_req.created_by,
        ),
    )
    document_id = cursor.lastrowid

    for item in inward_req.items:
        cursor.execute(
            """
            INSERT INTO inward_items (inward_document_id, item_name, measurement, quantity)
            VALUES (%s, %s, %s, %s)
            """,
            (document_id, item.item_name, item.measurement, item.quantity),
        )

    items_dict = [
        {"item_name": item.item_name, "measurement": item.measurement, "quantity": item.quantity}
        for item in inward_req.items
    ]
    _update_stock_for_inward_tx(conn, inward_req.ms_party_id, items_dict)

    cursor.close()

    doc_date_str = _ensure_doc_date_str(inward_req.document_date)
    main_event = create_inward_delta_event(
        document_id=document_id,
        ms_party_id=inward_req.ms_party_id,
        total_quantity=total_qty,
        inward_number=f"IN-{inward_num:06d}",
        document_date=doc_date_str,
    )
    stock_events = [
        create_stock_delta_event(
            party_id=inward_req.ms_party_id,
            item_name=item.item_name,
            measurement=item.measurement,
            delta=item.quantity,  # Inward: +qty
        )
        for item in inward_req.items
    ]

    return {
        "document_id": document_id,
        "main_event": (EVENT_INWARD_CREATED, "inward", document_id, main_event),
        "stock_events": [
            (EVENT_STOCK_DELTA_UPDATED, "stock", inward_req.ms_party_id, se) for se in stock_events
        ],
    }


def _process_transfer(conn, transfer_req: CreateTransferRequest) -> Dict:
    """Execute transfer creation inside the given transaction and return pending events."""
    cursor = conn.cursor()

    # Validations (reuse existing rules)
    for item in transfer_req.items:
        if item.measurement not in [15, 22]:
            raise HTTPException(status_code=400, detail=f"Invalid measurement: {item.measurement}")
    item_keys = [(item.item_name, item.measurement) for item in transfer_req.items]
    if len(item_keys) != len(set(item_keys)):
        raise HTTPException(status_code=400, detail="Duplicate item + measurement")

    cursor.execute("SELECT name FROM liabilities WHERE id = %s", (transfer_req.ms_party_id,))
    party_result = cursor.fetchone()
    if not party_result:
        raise HTTPException(status_code=404, detail="MS Party not found")
    party_name = party_result[0]

    # Generate numbers - separate counters for By Name transfers
    if transfer_req.transfer_type == "by_name":
        # By Name transfers use separate counters: TRANSFER_BN and SR_BN
        transfer_num = get_next_number("TRANSFER_BN")
        if transfer_num is None:
            raise HTTPException(status_code=500, detail="Failed to generate By Name transfer number")
        transfer_number_format = f"TRBN-{transfer_num:06d}"
        
        # Separate SR counter for By Name transfers
        sr_num = get_next_number("SR_BN", party_name)
        if sr_num is None:
            raise HTTPException(status_code=500, detail="Failed to generate By Name SR number")
    else:
        # Standard transfers use TRANSFER and SR counters
        transfer_num = get_next_number("TRANSFER")
        if transfer_num is None:
            raise HTTPException(status_code=500, detail="Failed to generate transfer number")
        transfer_number_format = f"TR-{transfer_num:06d}"
        
        sr_num = get_next_number("SR", party_name)
        if sr_num is None:
            raise HTTPException(status_code=500, detail="Failed to generate SR number")

    gp_num = transfer_num
    sr_number_format = f"SR-{sr_num:06d}"
    total_qty = sum(item.quantity for item in transfer_req.items)

    if transfer_req.transfer_type == "by_name":
        if not transfer_req.transfer_to_ms_party_id:
            raise HTTPException(status_code=400, detail="Transfer To MS Party is required for By Name Transfer")
        if transfer_req.transfer_to_ms_party_id == transfer_req.ms_party_id:
            raise HTTPException(status_code=400, detail="Transfer To MS Party cannot be the same as source MS Party")

    cursor.execute(
        """
        INSERT INTO transfer_documents 
        (transfer_number, gp_number, sr_number, ms_party_id, from_party,
         transfer_to, transfer_to_ms_party_id, transfer_type, vehicle_number, driver_name,
         total_quantity, document_date, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            transfer_number_format,
            f"GP-{gp_num:06d}",
            sr_number_format,
            transfer_req.ms_party_id,
            transfer_req.from_party,
            transfer_req.transfer_to,
            transfer_req.transfer_to_ms_party_id,
            transfer_req.transfer_type,
            transfer_req.vehicle_number,
            transfer_req.driver_name,
            total_qty,
            transfer_req.document_date,
            transfer_req.created_by,
        ),
    )
    document_id = cursor.lastrowid

    for item in transfer_req.items:
        cursor.execute(
            """
            INSERT INTO transfer_items (transfer_document_id, item_name, measurement, quantity)
            VALUES (%s, %s, %s, %s)
            """,
            (document_id, item.item_name, item.measurement, item.quantity),
        )

    items_dict = [
        {"item_name": item.item_name, "measurement": item.measurement, "quantity": item.quantity}
        for item in transfer_req.items
    ]
    
    # Handle stock updates based on transfer type
    stock_events = []
    if transfer_req.transfer_type == "by_name":
        # BN Transfer: Deduct from source, add to destination
        if not transfer_req.transfer_to_ms_party_id:
            raise HTTPException(status_code=400, detail="Transfer To MS Party is required for By Name Transfer")
        _update_stock_for_transfer_bn_tx(conn, transfer_req.ms_party_id, transfer_req.transfer_to_ms_party_id, items_dict)
        
        # Stock events for both source (out) and destination (in)
        for item in transfer_req.items:
            # Source party: deduct (negative delta)
            stock_events.append(
                create_stock_delta_event(
                    party_id=transfer_req.ms_party_id,
                    item_name=item.item_name,
                    measurement=item.measurement,
                    delta=-item.quantity,
                )
            )
            # Destination party: add (positive delta)
            stock_events.append(
                create_stock_delta_event(
                    party_id=transfer_req.transfer_to_ms_party_id,
                    item_name=item.item_name,
                    measurement=item.measurement,
                    delta=item.quantity,
                )
            )
    else:
        # Simple Transfer: Only deduct from source (no addition to destination)
        _update_stock_for_transfer_tx(conn, transfer_req.ms_party_id, items_dict)
        
        # Stock events only for source party (deduct)
        stock_events = [
            create_stock_delta_event(
                party_id=transfer_req.ms_party_id,
                item_name=item.item_name,
                measurement=item.measurement,
                delta=-item.quantity,
            )
            for item in transfer_req.items
        ]

    # Create ledger entries based on transfer type
    # Format document date for ledger entries
    doc_date_str = _ensure_doc_date_str(transfer_req.document_date)
    if isinstance(doc_date_str, str):
        try:
            doc_date = datetime.strptime(doc_date_str[:10], '%Y-%m-%d').date()
        except:
            doc_date = datetime.now().date()
    else:
        doc_date = datetime.now().date()
    
    if transfer_req.transfer_type == 'by_name':
        # Transfer By Name: Only party ledgers (NO UD ledger entry)
        # Get party ledger IDs
        party_a_ledger_id = get_party_ledger_id(conn, transfer_req.ms_party_id)
        transfer_to_ledger_id = get_party_ledger_id(conn, transfer_req.transfer_to_ms_party_id)
        
        if not party_a_ledger_id:
            raise HTTPException(status_code=500, detail=f"Ledger not found for party {party_name}")
        if not transfer_to_ledger_id:
            # Get transfer to party name
            cursor.execute("SELECT name FROM liabilities WHERE id = %s", (transfer_req.transfer_to_ms_party_id,))
            transfer_to_result = cursor.fetchone()
            transfer_to_party_name = transfer_to_result[0] if transfer_to_result else "Unknown Party"
            raise HTTPException(status_code=500, detail=f"Ledger not found for party {transfer_to_party_name}")
        
        # Get transfer to party name for ledger entries
        cursor.execute("SELECT name FROM liabilities WHERE id = %s", (transfer_req.transfer_to_ms_party_id,))
        transfer_to_result = cursor.fetchone()
        transfer_to_party_name = transfer_to_result[0] if transfer_to_result else "Unknown Party"
        
        # Create ledger entries for each item
        for item in transfer_req.items:
            qty_15 = item.quantity if item.measurement == 15 else 0.0
            qty_22 = item.quantity if item.measurement == 22 else 0.0
            total_qty = item.quantity
            
            # Party A Ledger Entry: Debit
            create_ledger_entry(
                conn, party_a_ledger_id, doc_date.isoformat(),
                "Transfer By Name #", transfer_number_format,
                transfer_to_party_name,  # Particulars
                "Stock transfer by name",  # Description
                item.item_name, qty_15, qty_22,
                total_qty, 0.0  # Debit, no credit
            )
            
            # Transfer To Party Ledger Entry: Credit
            create_ledger_entry(
                conn, transfer_to_ledger_id, doc_date.isoformat(),
                "Transfer By Name #", transfer_number_format,
                party_name,  # Particulars
                "Stock transfer by name",  # Description
                item.item_name, qty_15, qty_22,
                0.0, total_qty  # No debit, credit
            )
    else:
        # Simple Transfer: UD ledger + Party A ledger
        # Get ledger IDs
        ud_ledger_id = get_ud_ledger_id(conn)
        party_ledger_id = get_party_ledger_id(conn, transfer_req.ms_party_id)
        
        if not ud_ledger_id:
            raise HTTPException(status_code=500, detail="UD Ledger not found")
        if not party_ledger_id:
            raise HTTPException(status_code=500, detail=f"Ledger not found for party {party_name}")
        
        # Create ledger entries for each item
        for item in transfer_req.items:
            qty_15 = item.quantity if item.measurement == 15 else 0.0
            qty_22 = item.quantity if item.measurement == 22 else 0.0
            total_qty = item.quantity
            
            # UD Ledger Entry: Credit
            create_ledger_entry(
                conn, ud_ledger_id, doc_date.isoformat(),
                "Transfer #", transfer_number_format,
                party_name,  # Particulars
                f"Stock transfer to {transfer_req.transfer_to or 'N/A'}",  # Description
                item.item_name, qty_15, qty_22,
                0.0, total_qty  # No debit, credit
            )
            
            # Party A Ledger Entry: Debit
            create_ledger_entry(
                conn, party_ledger_id, doc_date.isoformat(),
                "Transfer #", transfer_number_format,
                "UNIVERSAL DYEING",  # Particulars
                f"Stock transfer to {transfer_req.transfer_to or 'N/A'}",  # Description
                item.item_name, qty_15, qty_22,
                total_qty, 0.0  # Debit, no credit
            )

    cursor.close()

    main_event = create_transfer_delta_event(
        document_id=document_id,
        ms_party_id=transfer_req.ms_party_id,
        total_quantity=total_qty,
        transfer_number=transfer_number_format,
        transfer_type=transfer_req.transfer_type,
        document_date=doc_date_str,
    )

    return {
        "document_id": document_id,
        "main_event": (EVENT_TRANSFER_CREATED, "transfer", document_id, main_event),
        "stock_events": [
            (EVENT_STOCK_DELTA_UPDATED, "stock", se["party_id"], se) for se in stock_events
        ],
    }


async def _emit_events(events: List[Tuple[str, str, int, Dict]]) -> List[int]:
    """Log and broadcast events after commit."""
    event_ids = []
    for event_type, entity_type, entity_id, payload in events:
        try:
            event_id = log_event(event_type=event_type, entity_type=entity_type, entity_id=entity_id, delta_data=payload)
            event_ids.append(event_id)
            await broadcast_message(payload)
        except Exception as e:
            print(f"Error emitting event {event_type}: {e}")
    return event_ids


# ==================== INWARD COMMAND ====================

@app.post("/api/command/inward/commit")
async def command_inward_commit(inward_req: CreateInwardRequest, request: Request):
    """Optimized inward creation (transactional, delta events after commit)."""
    client_ip = get_client_ip(request)
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        conn.autocommit = False

        result = _process_inward(conn, inward_req)
        conn.commit()

        all_events = [result["main_event"]] + result["stock_events"]
        event_ids = await _emit_events(all_events)
        main_event_id = event_ids[0] if event_ids else None

        return {
            "success": True,
            "event_id": main_event_id,
            "document_id": result["document_id"],
            "affected_entities": ["inward", "stock"],
        }
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"Command inward commit error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            conn.autocommit = True
            db_pool.return_connection(conn)


# ==================== TRANSFER COMMAND ====================

@app.post("/api/command/transfer/commit")
async def command_transfer_commit(transfer_req: CreateTransferRequest, request: Request):
    """Optimized transfer creation (transactional, delta events after commit)."""
    client_ip = get_client_ip(request)
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        conn.autocommit = False

        result = _process_transfer(conn, transfer_req)
        conn.commit()

        all_events = [result["main_event"]] + result["stock_events"]
        event_ids = await _emit_events(all_events)
        main_event_id = event_ids[0] if event_ids else None

        return {
            "success": True,
            "event_id": main_event_id,
            "document_id": result["document_id"],
            "affected_entities": ["transfer", "stock"],
        }
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"Command transfer commit error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            conn.autocommit = True
            db_pool.return_connection(conn)

