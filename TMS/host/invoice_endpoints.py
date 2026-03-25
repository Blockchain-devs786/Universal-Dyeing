"""Invoice API Endpoints"""

from fastapi import HTTPException, Request, Query
from datetime import datetime
from typing import List, Optional
from host.db_pool import db_pool
from host.stock_manager import get_next_number
from host.ledger_manager import post_invoice_to_ledgers, reverse_invoice_from_ledgers

# These will be imported from api_server when this module is loaded
from host.api_server import (
    app, rate_limit_check, get_client_ip,
    CreateInvoiceRequest, UpdateInvoiceRequest,
    broadcast_message
)


# ==================== INVOICE ENDPOINTS ====================

@app.get("/api/invoice")
async def get_invoices(request: Request):
    """Get all invoices"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT i.id, i.invoice_number, i.ms_party_id,
                   (SELECT name FROM liabilities WHERE id = i.ms_party_id) as ms_party_name,
                   i.number_of_items, i.discount_amount, i.discount_source,
                   i.total_amount, i.invoice_date, i.created_by, i.edited_by, i.edit_log_history, i.created_at
            FROM invoices i
            ORDER BY i.invoice_date DESC, i.invoice_number DESC
        """)
        invoices = cursor.fetchall()
        
        for invoice in invoices:
            if invoice['invoice_date']:
                invoice['invoice_date'] = invoice['invoice_date'].isoformat()
            if invoice['created_at']:
                invoice['created_at'] = invoice['created_at'].isoformat()
            invoice['discount_amount'] = float(invoice['discount_amount'])
            invoice['total_amount'] = float(invoice['total_amount'])
        
        cursor.close()
        return {"success": True, "invoices": invoices}
    except Exception as e:
        print(f"Get invoices error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/invoice/{invoice_id}")
async def get_invoice(invoice_id: int, request: Request):
    """Get a specific invoice with items"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT i.id, i.invoice_number, i.ms_party_id,
                   (SELECT name FROM liabilities WHERE id = i.ms_party_id) as ms_party_name,
                   i.number_of_items, i.discount_amount, i.discount_source,
                   i.total_amount, i.invoice_date, i.created_by, i.edited_by, i.edit_log_history, i.created_at
            FROM invoices i
            WHERE i.id = %s
        """, (invoice_id,))
        invoice = cursor.fetchone()
        
        if not invoice:
            cursor.close()
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        cursor.execute("""
            SELECT ii.id, ii.outward_document_id, ii.transfer_document_id,
                   COALESCE(od.outward_number, td.transfer_number) as document_number,
                   COALESCE(od.gp_number, td.gp_number) as gp_number,
                   CASE 
                       WHEN ii.outward_document_id IS NOT NULL THEN 'outward'
                       WHEN ii.transfer_document_id IS NOT NULL THEN 'transfer'
                   END as document_type,
                   ii.item_name, ii.measurement, ii.quantity, ii.rate, ii.amount
            FROM invoice_items ii
            LEFT JOIN outward_documents od ON ii.outward_document_id = od.id
            LEFT JOIN transfer_documents td ON ii.transfer_document_id = td.id
            WHERE ii.invoice_id = %s
            ORDER BY 
                CASE WHEN ii.outward_document_id IS NOT NULL THEN 1 ELSE 2 END,
                COALESCE(ii.outward_document_id, ii.transfer_document_id),
                ii.item_name, ii.measurement
        """, (invoice_id,))
        items = cursor.fetchall()
        
        if invoice['invoice_date']:
            invoice['invoice_date'] = invoice['invoice_date'].isoformat()
        if invoice['created_at']:
            invoice['created_at'] = invoice['created_at'].isoformat()
        invoice['discount_amount'] = float(invoice['discount_amount'])
        invoice['total_amount'] = float(invoice['total_amount'])
        
        for item in items:
            item['quantity'] = float(item['quantity'])
            item['rate'] = float(item['rate'])
            item['amount'] = float(item['amount'])
            # Add backward compatibility fields
            if item['document_type'] == 'outward':
                item['outward_number'] = item['document_number']
            elif item['document_type'] == 'transfer':
                item['outward_number'] = item['document_number']  # For backward compatibility
                item['transfer_number'] = item['document_number']
        
        invoice['items'] = items
        cursor.close()
        return {"success": True, "invoice": invoice}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get invoice error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/invoice/outwards/{ms_party_id}")
async def get_available_outwards(ms_party_id: int, request: Request, exclude_invoice_id: Optional[int] = Query(None)):
    """
    Get all outward documents for a specific MS Party that are not yet invoiced.

    Business rule (2026-01): Invoices can no longer be created from transfers,
    so this endpoint intentionally excludes ALL transfer documents. The response
    format is preserved for backward compatibility, but only outward documents
    are returned.
    """
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        
        # Get all outwards for this MS Party that are NOT already invoiced
        # OR are in the invoice being edited (if exclude_invoice_id is provided)
        if exclude_invoice_id:
            cursor.execute("""
                SELECT od.id, od.outward_number, od.gp_number, od.document_date, od.total_quantity, 'outward' as document_type
                FROM outward_documents od
                WHERE od.ms_party_id = %s
                AND (od.id NOT IN (
                    SELECT DISTINCT outward_document_id 
                    FROM invoice_items
                    WHERE invoice_id != %s AND outward_document_id IS NOT NULL
                ) OR od.id IN (
                    SELECT DISTINCT outward_document_id 
                    FROM invoice_items
                    WHERE invoice_id = %s AND outward_document_id IS NOT NULL
                ))
                ORDER BY od.document_date DESC, od.outward_number DESC
            """, (ms_party_id, exclude_invoice_id, exclude_invoice_id))
        else:
            cursor.execute("""
                SELECT od.id, od.outward_number, od.gp_number, od.document_date, od.total_quantity, 'outward' as document_type
                FROM outward_documents od
                WHERE od.ms_party_id = %s
                AND od.id NOT IN (
                    SELECT DISTINCT outward_document_id 
                    FROM invoice_items
                    WHERE outward_document_id IS NOT NULL
                )
                ORDER BY od.document_date DESC, od.outward_number DESC
            """, (ms_party_id,))
        outwards = cursor.fetchall()
        
        # Build response list (outwards only; transfers intentionally excluded)
        all_documents = []
        for outward in outwards:
            if outward['document_date']:
                outward['document_date'] = outward['document_date'].isoformat()
            outward['total_quantity'] = float(outward['total_quantity'])
            # Use outward_number for both types for consistency
            outward['document_number'] = outward['outward_number']
            all_documents.append(outward)
        
        cursor.close()
        return {"success": True, "outwards": all_documents}  # Keep key as "outwards" for backward compatibility
    except Exception as e:
        print(f"Get available outwards error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/invoice/outward/{outward_id}/items")
async def get_outward_items(outward_id: int, request: Request):
    """Get all items from a specific outward document"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT oi.id, oi.item_name, oi.measurement, oi.quantity,
                   od.outward_number, od.gp_number
            FROM outward_items oi
            JOIN outward_documents od ON oi.outward_document_id = od.id
            WHERE oi.outward_document_id = %s
            ORDER BY oi.item_name, oi.measurement
        """, (outward_id,))
        items = cursor.fetchall()
        
        for item in items:
            item['quantity'] = float(item['quantity'])
        
        cursor.close()
        return {"success": True, "items": items}
    except Exception as e:
        print(f"Get outward items error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/invoice/transfer/{transfer_id}/items")
async def get_transfer_items(transfer_id: int, request: Request):
    """Get all items from a specific transfer document (By Name Transfer)"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        
        # Verify it's a By Name Transfer
        cursor.execute("""
            SELECT transfer_type, transfer_number, gp_number
            FROM transfer_documents
            WHERE id = %s
        """, (transfer_id,))
        transfer_doc = cursor.fetchone()
        
        if not transfer_doc:
            cursor.close()
            raise HTTPException(status_code=404, detail="Transfer document not found")
        
        if transfer_doc['transfer_type'] != 'by_name':
            cursor.close()
            raise HTTPException(status_code=400, detail="Only By Name Transfers can be invoiced")
        
        cursor.execute("""
            SELECT ti.id, ti.item_name, ti.measurement, ti.quantity,
                   td.transfer_number, td.gp_number
            FROM transfer_items ti
            JOIN transfer_documents td ON ti.transfer_document_id = td.id
            WHERE ti.transfer_document_id = %s
            ORDER BY ti.item_name, ti.measurement
        """, (transfer_id,))
        items = cursor.fetchall()
        
        for item in items:
            item['quantity'] = float(item['quantity'])
            # Map transfer_number to outward_number for backward compatibility
            item['outward_number'] = item['transfer_number']
        
        cursor.close()
        return {"success": True, "items": items}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get transfer items error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/api/invoice")
async def create_invoice(invoice_req: CreateInvoiceRequest, request: Request):
    """Create a new invoice"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)
        
        # Validate that all outward documents belong to the same MS Party.
        # Business rule (2026-01): Invoices cannot be created from transfers,
        # so any transfer_document_id in the payload is rejected.
        outward_ids = []
        transfer_ids = []
        for item in invoice_req.items:
            if item.transfer_document_id:
                conn.rollback()
                cursor.close()
                raise HTTPException(status_code=400, detail="Invoices cannot be created from transfers")
            if item.outward_document_id:
                outward_ids.append(item.outward_document_id)
        
        if outward_ids:
            placeholders = ','.join(['%s'] * len(outward_ids))
            cursor.execute(f"""
                SELECT DISTINCT ms_party_id 
                FROM outward_documents 
                WHERE id IN ({placeholders})
            """, tuple(outward_ids))
            party_ids = [row['ms_party_id'] for row in cursor.fetchall()]
            
            if len(party_ids) > 1:
                conn.rollback()
                cursor.close()
                raise HTTPException(status_code=400, detail="All outwards must belong to the same MS Party")
            
            if party_ids and party_ids[0] != invoice_req.ms_party_id:
                conn.rollback()
                cursor.close()
                raise HTTPException(status_code=400, detail="MS Party ID mismatch with outward documents")
            
            # Check if any outward is already invoiced
            cursor.execute(f"""
                SELECT DISTINCT outward_document_id 
                FROM invoice_items 
                WHERE outward_document_id IN ({placeholders}) AND outward_document_id IS NOT NULL
            """, tuple(outward_ids))
            already_invoiced = [row['outward_document_id'] for row in cursor.fetchall()]
            
            if already_invoiced:
                conn.rollback()
                cursor.close()
                raise HTTPException(
                    status_code=400, 
                    detail=f"Outward documents {already_invoiced} are already invoiced"
                )
        
        
        # Generate invoice number
        invoice_num = get_next_number("INVOICE")
        if invoice_num is None:
            conn.rollback()
            cursor.close()
            raise HTTPException(status_code=500, detail="Failed to generate invoice number")
        
        invoice_number = f"INV-{invoice_num:06d}"
        
        # Calculate totals
        number_of_items = len(invoice_req.items)
        total_amount = sum(item.amount for item in invoice_req.items)
        final_total = total_amount - invoice_req.discount_amount
        
        # Insert invoice
        cursor.execute("""
            INSERT INTO invoices 
            (invoice_number, ms_party_id, number_of_items, discount_amount, discount_source,
             total_amount, invoice_date, created_by, edited_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL)
        """, (
            invoice_number, invoice_req.ms_party_id, number_of_items,
            invoice_req.discount_amount, invoice_req.discount_source,
            final_total, invoice_req.invoice_date, invoice_req.created_by
        ))
        invoice_id = cursor.lastrowid
        
        # Insert invoice items (outwards only; transfers not allowed)
        for item in invoice_req.items:
            # Transfers are no longer allowed on invoices
            if item.transfer_document_id:
                conn.rollback()
                cursor.close()
                raise HTTPException(status_code=400, detail="Invoice items cannot reference transfers")
            
            if not item.outward_document_id:
                conn.rollback()
                cursor.close()
                raise HTTPException(status_code=400, detail="Invoice items must reference an outward document")
            
            cursor.execute("""
                INSERT INTO invoice_items 
                (invoice_id, outward_document_id, transfer_document_id, item_name, measurement, quantity, rate, amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                invoice_id, item.outward_document_id, item.transfer_document_id, item.item_name,
                item.measurement, item.quantity, item.rate, item.amount
            ))
        
        # Post to financial ledgers
        if not post_invoice_to_ledgers(invoice_id, conn):
            conn.rollback()
            cursor.close()
            raise HTTPException(status_code=500, detail="Failed to post invoice to ledgers")
        
        conn.commit()
        cursor.close()

        # Fetch created invoice summary (matches `/api/invoice` list fields) for instant UI patching
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT i.id, i.invoice_number, i.ms_party_id,
                   (SELECT name FROM liabilities WHERE id = i.ms_party_id) as ms_party_name,
                   i.number_of_items, i.discount_amount, i.discount_source,
                   i.total_amount, i.invoice_date, i.created_by, i.edited_by, i.created_at
            FROM invoices i
            WHERE i.id = %s
        """, (invoice_id,))
        created_invoice = cursor.fetchone()
        cursor.close()

        if created_invoice:
            if created_invoice.get('invoice_date'):
                created_invoice['invoice_date'] = created_invoice['invoice_date'].isoformat()
            if created_invoice.get('created_at'):
                created_invoice['created_at'] = created_invoice['created_at'].isoformat()
            created_invoice['discount_amount'] = float(created_invoice.get('discount_amount', 0))
            created_invoice['total_amount'] = float(created_invoice.get('total_amount', 0))

        # Broadcast real-time change (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "invoice",
                "action": "created",
                "data": created_invoice or {"id": invoice_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting invoice created: {e}")

        return {"success": True, "message": "Invoice created successfully", "invoice_id": invoice_id, "invoice": created_invoice}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"Create invoice error: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.put("/api/invoice/{invoice_id}")
async def update_invoice(invoice_id: int, invoice_req: UpdateInvoiceRequest, request: Request):
    """Update an existing invoice"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    if invoice_req.invoice_id != invoice_id:
        raise HTTPException(status_code=400, detail="Invoice ID mismatch")
    
    # Get username from request headers for edited_by
    from host.api_server import _get_username_from_request
    edited_by = _get_username_from_request(request)
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)
        
        # Get existing invoice with all fields for edit log
        cursor.execute("""
            SELECT id, ms_party_id, number_of_items, discount_amount, discount_source,
                   total_amount, invoice_date, invoice_number
            FROM invoices WHERE id = %s
        """, (invoice_id,))
        existing_invoice = cursor.fetchone()
        if not existing_invoice:
            conn.rollback()
            cursor.close()
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        invoice_number = existing_invoice.get('invoice_number')
        
        # Get old invoice items with outward_document_id for tracking outward changes
        cursor.execute("""
            SELECT item_name, measurement, quantity, rate, amount, outward_document_id
            FROM invoice_items
            WHERE invoice_id = %s
        """, (invoice_id,))
        old_items = cursor.fetchall()
        
        # Get old outward document IDs (distinct) and fetch their numbers
        old_outward_ids = set()
        for item in old_items:
            if item.get('outward_document_id'):
                old_outward_ids.add(item['outward_document_id'])
        
        # Get outward numbers for display in edit log
        old_outward_numbers = {}
        if old_outward_ids:
            placeholders = ','.join(['%s'] * len(old_outward_ids))
            cursor.execute(f"""
                SELECT id, outward_number FROM outward_documents WHERE id IN ({placeholders})
            """, tuple(old_outward_ids))
            for row in cursor.fetchall():
                old_outward_numbers[row['id']] = row['outward_number']
        
        # Get party names for edit log
        party_ids = {existing_invoice.get('ms_party_id'), invoice_req.ms_party_id}
        # Remove None values
        party_ids = {pid for pid in party_ids if pid is not None}
        party_names = {}
        if party_ids:
            placeholders = ','.join(['%s'] * len(party_ids))
            cursor.execute(f"""
                SELECT id, name FROM liabilities WHERE id IN ({placeholders})
            """, tuple(party_ids))
            for row in cursor.fetchall():
                party_names[row['id']] = row['name']
        
        # Reverse old entries from financial ledgers
        if not reverse_invoice_from_ledgers(invoice_number, conn):
            conn.rollback()
            cursor.close()
            raise HTTPException(status_code=500, detail="Failed to reverse old ledger entries")
        
        # Validate that all outward documents belong to the same MS Party.
        # Business rule (2026-01): Invoices cannot be updated to include transfers,
        # so any transfer_document_id in the payload is rejected.
        if invoice_req.outward_document_ids:
            placeholders = ','.join(['%s'] * len(invoice_req.outward_document_ids))
            cursor.execute(f"""
                SELECT DISTINCT ms_party_id 
                FROM outward_documents 
                WHERE id IN ({placeholders})
            """, tuple(invoice_req.outward_document_ids))
            party_ids = [row['ms_party_id'] for row in cursor.fetchall()]
            
            if len(party_ids) > 1:
                conn.rollback()
                cursor.close()
                raise HTTPException(status_code=400, detail="All outwards must belong to the same MS Party")
            
            if party_ids and party_ids[0] != invoice_req.ms_party_id:
                conn.rollback()
                cursor.close()
                raise HTTPException(status_code=400, detail="MS Party ID mismatch with outward documents")
            
            # Check if any outward is already invoiced in a different invoice
            cursor.execute(f"""
                SELECT DISTINCT ii.outward_document_id 
                FROM invoice_items ii
                JOIN invoices i ON ii.invoice_id = i.id
                WHERE ii.outward_document_id IN ({placeholders})
                AND i.id != %s
            """, tuple(list(invoice_req.outward_document_ids) + [invoice_id]))
            already_invoiced = [row['outward_document_id'] for row in cursor.fetchall()]
            
            if already_invoiced:
                conn.rollback()
                cursor.close()
                raise HTTPException(
                    status_code=400, 
                    detail=f"Outward documents {already_invoiced} are already invoiced in another invoice"
                )
        
        # Ensure no transfer_document_id is present in items (transfers not allowed)
        for item in invoice_req.items:
            if item.transfer_document_id:
                conn.rollback()
                cursor.close()
                raise HTTPException(status_code=400, detail="Invoice items cannot reference transfers")
        
        # Calculate totals
        number_of_items = len(invoice_req.items)
        total_amount = sum(item.amount for item in invoice_req.items)
        final_total = total_amount - invoice_req.discount_amount
        
        # Prepare new invoice data for edit log
        new_doc = {
            'ms_party_id': invoice_req.ms_party_id,
            'number_of_items': number_of_items,
            'discount_amount': invoice_req.discount_amount,
            'discount_source': invoice_req.discount_source,
            'total_amount': final_total,
            'invoice_date': invoice_req.invoice_date
        }
        
        # Prepare new items for edit log
        new_items = [
            {'item_name': item.item_name, 'measurement': item.measurement, 
             'quantity': item.quantity, 'rate': item.rate, 'amount': item.amount,
             'outward_document_id': item.outward_document_id}
            for item in invoice_req.items
        ]
        
        # Get new outward document IDs (distinct) - use invoice_req.outward_document_ids if available
        new_outward_ids = set()
        if invoice_req.outward_document_ids:
            new_outward_ids = set(invoice_req.outward_document_ids)
        else:
            # Fallback: extract from items
            for item in invoice_req.items:
                if item.outward_document_id:
                    new_outward_ids.add(item.outward_document_id)
        
        # Get new outward numbers for display in edit log
        new_outward_numbers = {}
        if new_outward_ids:
            placeholders = ','.join(['%s'] * len(new_outward_ids))
            cursor.execute(f"""
                SELECT id, outward_number FROM outward_documents WHERE id IN ({placeholders})
            """, tuple(new_outward_ids))
            for row in cursor.fetchall():
                new_outward_numbers[row['id']] = row['outward_number']
        
        # Generate edit log with outward tracking
        from host.edit_log_generator import generate_invoice_edit_log
        try:
            edit_log = generate_invoice_edit_log(existing_invoice, new_doc, old_items, new_items, party_names, 
                                                old_outward_ids, new_outward_ids, old_outward_numbers, new_outward_numbers)
        except Exception as e:
            print(f"Error generating edit log: {e}")
            import traceback
            traceback.print_exc()
            # Continue with update even if edit log generation fails
            edit_log = f"Error generating edit log: {str(e)}"
        
        # Update invoice (set edited_by and edit_log_history on update, never change created_by)
        cursor.execute("""
            UPDATE invoices 
            SET ms_party_id = %s, number_of_items = %s, discount_amount = %s, discount_source = %s,
                total_amount = %s, invoice_date = %s, edited_by = %s, edit_log_history = %s
            WHERE id = %s
        """, (
            invoice_req.ms_party_id, number_of_items,
            invoice_req.discount_amount, invoice_req.discount_source,
            final_total, invoice_req.invoice_date, edited_by, edit_log, invoice_id
        ))
        
        # Delete old invoice items
        cursor.execute("DELETE FROM invoice_items WHERE invoice_id = %s", (invoice_id,))
        
        # Insert new invoice items (outwards only)
        for item in invoice_req.items:
            # Transfers are no longer allowed on invoices
            if item.transfer_document_id:
                conn.rollback()
                cursor.close()
                raise HTTPException(status_code=400, detail="Invoice items cannot reference transfers")
            
            if not item.outward_document_id:
                conn.rollback()
                cursor.close()
                raise HTTPException(status_code=400, detail="Invoice items must reference an outward document")
            
            cursor.execute("""
                INSERT INTO invoice_items 
                (invoice_id, outward_document_id, transfer_document_id, item_name, measurement, quantity, rate, amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                invoice_id, item.outward_document_id, item.transfer_document_id, item.item_name,
                item.measurement, item.quantity, item.rate, item.amount
            ))
        
        # Post new entries to financial ledgers
        if not post_invoice_to_ledgers(invoice_id, conn):
            conn.rollback()
            cursor.close()
            raise HTTPException(status_code=500, detail="Failed to post updated invoice to ledgers")
        
        conn.commit()
        cursor.close()

        # Fetch updated invoice summary for instant UI patching
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT i.id, i.invoice_number, i.ms_party_id,
                   (SELECT name FROM liabilities WHERE id = i.ms_party_id) as ms_party_name,
                   i.number_of_items, i.discount_amount, i.discount_source,
                   i.total_amount, i.invoice_date, i.created_by, i.edited_by, i.edit_log_history, i.created_at
            FROM invoices i
            WHERE i.id = %s
        """, (invoice_id,))
        updated_invoice = cursor.fetchone()
        cursor.close()

        if updated_invoice:
            if updated_invoice.get('invoice_date'):
                updated_invoice['invoice_date'] = updated_invoice['invoice_date'].isoformat()
            if updated_invoice.get('created_at'):
                updated_invoice['created_at'] = updated_invoice['created_at'].isoformat()
            updated_invoice['discount_amount'] = float(updated_invoice.get('discount_amount', 0))
            updated_invoice['total_amount'] = float(updated_invoice.get('total_amount', 0))

        # Broadcast real-time change (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "invoice",
                "action": "updated",
                "data": updated_invoice or {"id": invoice_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting invoice updated: {e}")

        return {"success": True, "message": "Invoice updated successfully", "invoice": updated_invoice}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Update invoice error: {e}")
        print(f"Traceback: {error_details}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.delete("/api/invoice/{invoice_id}")
async def delete_invoice(invoice_id: int, request: Request):
    """Delete an invoice"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        conn.autocommit = False
        cursor = conn.cursor()
        
        # Check if invoice exists
        cursor.execute("SELECT id, invoice_number FROM invoices WHERE id = %s", (invoice_id,))
        invoice_row = cursor.fetchone()
        if not invoice_row:
            conn.rollback()
            cursor.close()
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        invoice_number = invoice_row[1]
        
        # Reverse entries from financial ledgers
        if not reverse_invoice_from_ledgers(invoice_number, conn):
            conn.rollback()
            cursor.close()
            raise HTTPException(status_code=500, detail="Failed to reverse ledger entries")
        
        # Delete invoice (cascade will delete invoice_items)
        cursor.execute("DELETE FROM invoices WHERE id = %s", (invoice_id,))
        
        conn.commit()
        cursor.close()

        # Broadcast real-time change (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "invoice",
                "action": "deleted",
                "data": {"id": invoice_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting invoice deleted: {e}")

        return {"success": True, "message": "Invoice deleted successfully", "invoice_id": invoice_id}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"Delete invoice error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)

