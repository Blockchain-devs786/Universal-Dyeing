"""Data Entry API Endpoints (Inward, Transfer, Outward)"""

from fastapi import HTTPException, Request
from datetime import datetime
from typing import List, Optional
from host.db_pool import db_pool
from host.stock_manager import (
    get_next_number, update_stock_for_inward, update_stock_for_transfer,
    update_stock_for_outward, get_ud_ledger_id, get_party_ledger_id,
    create_ledger_entry, delete_ledger_entries_by_transaction
)

# These will be imported from api_server when this module is loaded
# (api_server imports this at the end, so app is already defined)
from host.api_server import (
    app, rate_limit_check, get_client_ip,
    CreateInwardRequest, UpdateInwardRequest,
    CreateTransferRequest, UpdateTransferRequest,
    CreateOutwardRequest, UpdateOutwardRequest,
    broadcast_message
)


# ==================== INWARD ENDPOINTS ====================

@app.get("/api/inward")
async def get_inward_documents(request: Request):
    """Get all inward documents"""
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
            SELECT id, inward_number, gp_number, sr_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   from_party, vehicle_number, driver_name, total_quantity,
                   document_date, created_by, edited_by, edit_log_history, created_at
            FROM inward_documents
            ORDER BY document_date DESC, inward_number DESC
        """)
        documents = cursor.fetchall()
        
        for doc in documents:
            if doc['document_date']:
                doc['document_date'] = doc['document_date'].isoformat()
            if doc['created_at']:
                doc['created_at'] = doc['created_at'].isoformat()
            doc['total_quantity'] = float(doc['total_quantity'])
        
        cursor.close()
        return {"success": True, "documents": documents}
    except Exception as e:
        print(f"Get inward documents error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/inward/{inward_id}")
async def get_inward_document(inward_id: int, request: Request):
    """Get a specific inward document with items"""
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
            SELECT id, inward_number, gp_number, sr_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   from_party, vehicle_number, driver_name, total_quantity,
                   document_date, created_by, edited_by, edit_log_history, created_at
            FROM inward_documents
            WHERE id = %s
        """, (inward_id,))
        document = cursor.fetchone()
        
        if not document:
            cursor.close()
            raise HTTPException(status_code=404, detail="Document not found")
        
        cursor.execute("""
            SELECT item_name, measurement, quantity
            FROM inward_items
            WHERE inward_document_id = %s
            ORDER BY item_name, measurement
        """, (inward_id,))
        items = cursor.fetchall()
        
        if document['document_date']:
            document['document_date'] = document['document_date'].isoformat()
        if document['created_at']:
            document['created_at'] = document['created_at'].isoformat()
        document['total_quantity'] = float(document['total_quantity'])
        
        for item in items:
            item['quantity'] = float(item['quantity'])
        
        document['items'] = items
        cursor.close()
        return {"success": True, "document": document}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get inward document error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/api/inward")
async def create_inward(inward_req: CreateInwardRequest, request: Request):
    """Create a new inward document"""
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
        
        # Validate measurements and quantities
        for item in inward_req.items:
            if item.measurement not in [15, 22]:
                raise HTTPException(status_code=400, detail=f"Invalid measurement: {item.measurement}. Must be 15 or 22")
            if item.quantity <= 0:
                raise HTTPException(status_code=400, detail=f"Quantity must be greater than 0 for {item.item_name} ({item.measurement})")
        
        # Check for duplicate items
        item_keys = [(item.item_name, item.measurement) for item in inward_req.items]
        if len(item_keys) != len(set(item_keys)):
            raise HTTPException(status_code=400, detail="Duplicate item + measurement combination")
        
        # Get party name for SR number
        cursor.execute("SELECT name FROM liabilities WHERE id = %s", (inward_req.ms_party_id,))
        party_result = cursor.fetchone()
        if not party_result:
            raise HTTPException(status_code=404, detail="MS Party not found")
        party_name = party_result.get('name')
        
        # Generate numbers
        inward_num = get_next_number("INWARD")
        if inward_num is None:
            raise HTTPException(status_code=500, detail="Failed to generate inward number")
        
        gp_num = inward_num  # GP # = Document #
        sr_num = get_next_number("SR", party_name)
        if sr_num is None:
            raise HTTPException(status_code=500, detail="Failed to generate SR number")
        
        # Calculate total quantity
        total_qty = sum(item.quantity for item in inward_req.items)
        
        # Insert document
        cursor.execute("""
            INSERT INTO inward_documents 
            (inward_number, gp_number, sr_number, ms_party_id, from_party,
             vehicle_number, driver_name, total_quantity, document_date, created_by, edited_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
        """, (f"IN-{inward_num:06d}", f"GP-{gp_num:06d}", f"SR-{sr_num:06d}",
              inward_req.ms_party_id, inward_req.from_party,
              inward_req.vehicle_number, inward_req.driver_name,
              total_qty, inward_req.document_date, inward_req.created_by))
        
        document_id = cursor.lastrowid
        
        # Insert items
        for item in inward_req.items:
            cursor.execute("""
                INSERT INTO inward_items (inward_document_id, item_name, measurement, quantity)
                VALUES (%s, %s, %s, %s)
            """, (document_id, item.item_name, item.measurement, item.quantity))
        
        # Update stock
        items_dict = [{"item_name": item.item_name, "measurement": item.measurement, "quantity": item.quantity}
                     for item in inward_req.items]
        if not update_stock_for_inward(inward_req.ms_party_id, items_dict):
            raise HTTPException(status_code=500, detail="Failed to update stock")
        
        # Get party name for ledger entries
        cursor.execute("SELECT name FROM liabilities WHERE id = %s", (inward_req.ms_party_id,))
        party_name_result = cursor.fetchone()
        party_name = party_name_result.get('name') if party_name_result else "Unknown Party"
        
        # Get ledger IDs
        ud_ledger_id = get_ud_ledger_id(conn)
        party_ledger_id = get_party_ledger_id(conn, inward_req.ms_party_id)
        
        if not ud_ledger_id:
            raise HTTPException(status_code=500, detail="UD Ledger not found")
        if not party_ledger_id:
            raise HTTPException(status_code=500, detail=f"Ledger not found for party {party_name}")
        
        # Format document date
        doc_date_str = inward_req.document_date
        if isinstance(doc_date_str, str):
            try:
                doc_date = datetime.strptime(doc_date_str[:10], '%Y-%m-%d').date()
            except:
                doc_date = datetime.now().date()
        else:
            doc_date = doc_date_str if hasattr(doc_date_str, 'isoformat') else datetime.now().date()
        
        inward_number = f"IN-{inward_num:06d}"
        
        # Create ledger entries for each item
        for item in inward_req.items:
            qty_15 = item.quantity if item.measurement == 15 else 0.0
            qty_22 = item.quantity if item.measurement == 22 else 0.0
            total_qty = item.quantity
            
            # UD Ledger Entry: Debit
            create_ledger_entry(
                conn, ud_ledger_id, doc_date.isoformat(),
                "Inward #", inward_number,
                party_name,  # Particulars
                f"Stock received from {inward_req.from_party}",  # Description
                item.item_name, qty_15, qty_22,
                total_qty, 0.0  # Debit, no credit
            )
            
            # Party Ledger Entry: Credit
            create_ledger_entry(
                conn, party_ledger_id, doc_date.isoformat(),
                "Inward #", inward_number,
                "UNIVERSAL DYEING",  # Particulars
                f"Stock sent from {inward_req.from_party}",  # Description
                item.item_name, qty_15, qty_22,
                0.0, total_qty  # No debit, credit
            )
        
        conn.commit()
        cursor.close()

        # Fetch created document summary (matches `/api/inward` list fields) for instant UI patching
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, inward_number, gp_number, sr_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   from_party, vehicle_number, driver_name, total_quantity,
                   document_date, created_by, edited_by, edit_log_history, created_at
            FROM inward_documents
            WHERE id = %s
        """, (document_id,))
        created_doc = cursor.fetchone()
        cursor.close()

        if created_doc:
            if created_doc.get('document_date'):
                created_doc['document_date'] = created_doc['document_date'].isoformat()
            if created_doc.get('created_at'):
                created_doc['created_at'] = created_doc['created_at'].isoformat()
            created_doc['total_quantity'] = float(created_doc.get('total_quantity', 0))

        # Broadcast real-time change (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "inward",
                "action": "created",
                "data": created_doc or {"id": document_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting inward created: {e}")

        return {
            "success": True,
            "message": "Inward document created successfully",
            "document_id": document_id,
            "document": created_doc
        }
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"Create inward error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            conn.autocommit = True
            db_pool.return_connection(conn)


@app.put("/api/inward")
async def update_inward(inward_req: UpdateInwardRequest, request: Request):
    """Update an inward document"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
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
        
        # Get existing document with all fields for edit log
        cursor.execute("""
            SELECT id, ms_party_id, from_party, vehicle_number, driver_name, 
                   document_date, total_quantity, inward_number
            FROM inward_documents WHERE id = %s
        """, (inward_req.inward_id,))
        existing = cursor.fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Document not found")
        
        old_inward_number = existing.get('inward_number')
        old_ms_party_id = existing.get('ms_party_id')
        
        # Get existing items
        cursor.execute("""
            SELECT item_name, measurement, quantity
            FROM inward_items
            WHERE inward_document_id = %s
        """, (inward_req.inward_id,))
        old_items = cursor.fetchall()
        
        # Get party names for edit log
        party_ids = {existing.get('ms_party_id'), inward_req.ms_party_id}
        party_names = {}
        if party_ids:
            placeholders = ','.join(['%s'] * len(party_ids))
            cursor.execute(f"""
                SELECT id, name FROM liabilities WHERE id IN ({placeholders})
            """, tuple(party_ids))
            for row in cursor.fetchall():
                party_names[row['id']] = row['name']
        
        # Reverse old stock within the same transaction
        for item in old_items:
            item_name = item['item_name']
            measurement = item['measurement']
            quantity = -float(item['quantity'])  # Negative because we're reversing
            
            # Check if stock record exists before reversing
            cursor.execute("""
                SELECT id FROM stock 
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (old_ms_party_id, item_name, measurement))
            
            stock_result = cursor.fetchone()
            if not stock_result:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot reverse stock: Stock record not found for {item_name} ({measurement})"
                )
            
            # Update stock - subtract from total_inward
            cursor.execute("""
                UPDATE stock SET total_inward = total_inward + %s
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (quantity, old_ms_party_id, item_name, measurement))
            
            # Verify the update affected a row
            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to reverse stock for {item_name} ({measurement})"
                )
        
        # Delete old ledger entries
        if old_inward_number:
            delete_ledger_entries_by_transaction(conn, old_inward_number)
        
        # Validate new items
        for item in inward_req.items:
            if item.measurement not in [15, 22]:
                raise HTTPException(status_code=400, detail=f"Invalid measurement: {item.measurement}")
            if item.quantity <= 0:
                raise HTTPException(status_code=400, detail=f"Quantity must be greater than 0 for {item.item_name} ({item.measurement})")
        
        item_keys = [(item.item_name, item.measurement) for item in inward_req.items]
        if len(item_keys) != len(set(item_keys)):
            raise HTTPException(status_code=400, detail="Duplicate item + measurement")
        
        # Calculate total
        total_qty = sum(item.quantity for item in inward_req.items)
        
        # Prepare new document data for edit log
        new_doc = {
            'ms_party_id': inward_req.ms_party_id,
            'from_party': inward_req.from_party or '',
            'vehicle_number': inward_req.vehicle_number or '',
            'driver_name': inward_req.driver_name or '',
            'document_date': inward_req.document_date,
            'total_quantity': total_qty
        }
        
        # Prepare new items for edit log
        new_items = [
            {'item_name': item.item_name, 'measurement': item.measurement, 'quantity': item.quantity}
            for item in inward_req.items
        ]
        
        # Generate edit log
        from host.edit_log_generator import generate_inward_edit_log
        edit_log = generate_inward_edit_log(existing, new_doc, old_items, new_items, party_names)
        
        # Update document (set edited_by and edit_log_history on update, never change created_by)
        cursor.execute("""
            UPDATE inward_documents
            SET ms_party_id = %s, from_party = %s, vehicle_number = %s,
                driver_name = %s, total_quantity = %s, document_date = %s, 
                edited_by = %s, edit_log_history = %s
            WHERE id = %s
        """, (inward_req.ms_party_id, inward_req.from_party, inward_req.vehicle_number,
              inward_req.driver_name, total_qty, inward_req.document_date, edited_by, edit_log, inward_req.inward_id))
        
        # Delete old items
        cursor.execute("DELETE FROM inward_items WHERE inward_document_id = %s", (inward_req.inward_id,))
        
        # Insert new items
        for item in inward_req.items:
            cursor.execute("""
                INSERT INTO inward_items (inward_document_id, item_name, measurement, quantity)
                VALUES (%s, %s, %s, %s)
            """, (inward_req.inward_id, item.item_name, item.measurement, item.quantity))
        
        # Update stock with new items within the same transaction
        for item in inward_req.items:
            item_name = item.item_name
            measurement = item.measurement
            quantity = item.quantity
            
            # Check if stock record exists
            cursor.execute("""
                SELECT id FROM stock 
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (inward_req.ms_party_id, item_name, measurement))
            
            result = cursor.fetchone()
            
            if result:
                # Update existing stock
                cursor.execute("""
                    UPDATE stock SET total_inward = total_inward + %s
                    WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
                """, (quantity, inward_req.ms_party_id, item_name, measurement))
                
                # Verify the update affected a row
                if cursor.rowcount == 0:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to update stock for {item_name} ({measurement})"
                    )
            else:
                # Create new stock record
                cursor.execute("""
                    INSERT INTO stock (ms_party_id, item_name, measurement, total_inward)
                    VALUES (%s, %s, %s, %s)
                """, (inward_req.ms_party_id, item_name, measurement, quantity))
        
        # Get updated inward_number for new ledger entries
        cursor.execute("SELECT inward_number FROM inward_documents WHERE id = %s", (inward_req.inward_id,))
        updated_doc = cursor.fetchone()
        new_inward_number = updated_doc.get('inward_number') if updated_doc else None
        
        # Get party name for ledger entries
        cursor.execute("SELECT name FROM liabilities WHERE id = %s", (inward_req.ms_party_id,))
        party_name_result = cursor.fetchone()
        party_name = party_name_result.get('name') if party_name_result else "Unknown Party"
        
        # Get ledger IDs
        ud_ledger_id = get_ud_ledger_id(conn)
        party_ledger_id = get_party_ledger_id(conn, inward_req.ms_party_id)
        
        if not ud_ledger_id:
            raise HTTPException(status_code=500, detail="UD Ledger not found")
        if not party_ledger_id:
            raise HTTPException(status_code=500, detail=f"Ledger not found for party ID {inward_req.ms_party_id}")
        
        if new_inward_number:
            # Format document date
            doc_date_str = inward_req.document_date
            if isinstance(doc_date_str, str):
                try:
                    doc_date = datetime.strptime(doc_date_str[:10], '%Y-%m-%d').date()
                except:
                    doc_date = datetime.now().date()
            else:
                doc_date = doc_date_str if hasattr(doc_date_str, 'isoformat') else datetime.now().date()
            
            # Create new ledger entries for each item
            for item in inward_req.items:
                qty_15 = item.quantity if item.measurement == 15 else 0.0
                qty_22 = item.quantity if item.measurement == 22 else 0.0
                total_qty = item.quantity
                
                # UD Ledger Entry: Debit
                create_ledger_entry(
                    conn, ud_ledger_id, doc_date.isoformat(),
                    "Inward #", new_inward_number,
                    party_name,  # Particulars
                    f"Stock received from {inward_req.from_party}",  # Description
                    item.item_name, qty_15, qty_22,
                    total_qty, 0.0  # Debit, no credit
                )
                
                # Party Ledger Entry: Credit
                create_ledger_entry(
                    conn, party_ledger_id, doc_date.isoformat(),
                    "Inward #", new_inward_number,
                    "UNIVERSAL DYEING",  # Particulars
                    f"Stock sent from {inward_req.from_party}",  # Description
                    item.item_name, qty_15, qty_22,
                    0.0, total_qty  # No debit, credit
                )
        
        conn.commit()
        cursor.close()

        # Fetch updated document summary for instant UI patching
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, inward_number, gp_number, sr_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   from_party, vehicle_number, driver_name, total_quantity,
                   document_date, created_by, edited_by, edit_log_history, created_at
            FROM inward_documents
            WHERE id = %s
        """, (inward_req.inward_id,))
        updated_doc = cursor.fetchone()
        cursor.close()

        if updated_doc:
            if updated_doc.get('document_date'):
                updated_doc['document_date'] = updated_doc['document_date'].isoformat()
            if updated_doc.get('created_at'):
                updated_doc['created_at'] = updated_doc['created_at'].isoformat()
            updated_doc['total_quantity'] = float(updated_doc.get('total_quantity', 0))

        # Broadcast real-time change (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "inward",
                "action": "updated",
                "data": updated_doc or {"id": inward_req.inward_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting inward updated: {e}")

        return {"success": True, "message": "Inward document updated successfully", "document": updated_doc}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Update inward error: {e}")
        print(f"Traceback: {error_details}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            conn.autocommit = True
            db_pool.return_connection(conn)


@app.delete("/api/inward/{inward_id}")
async def delete_inward(inward_id: int, request: Request):
    """Delete an inward document"""
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
        
        # Get document with inward_number
        cursor.execute("""
            SELECT id, ms_party_id, inward_number FROM inward_documents WHERE id = %s
        """, (inward_id,))
        document = cursor.fetchone()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        inward_number = document.get('inward_number')
        
        cursor.execute("""
            SELECT item_name, measurement, quantity
            FROM inward_items
            WHERE inward_document_id = %s
        """, (inward_id,))
        items = cursor.fetchall()
        
        # Reverse stock within the same transaction
        for item in items:
            item_name = item['item_name']
            measurement = item['measurement']
            quantity = -float(item['quantity'])  # Negative because we're reversing
            
            # Update stock - subtract from total_inward
            cursor.execute("""
                UPDATE stock SET total_inward = total_inward + %s
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (quantity, document['ms_party_id'], item_name, measurement))
        
        # Delete ledger entries for this transaction
        if inward_number:
            delete_ledger_entries_by_transaction(conn, inward_number)
        
        # Delete document (items will be deleted via CASCADE)
        cursor.execute("DELETE FROM inward_documents WHERE id = %s", (inward_id,))
        
        conn.commit()
        cursor.close()

        # Broadcast real-time change (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "inward",
                "action": "deleted",
                "data": {"id": inward_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting inward deleted: {e}")

        return {"success": True, "message": "Inward document deleted successfully", "document_id": inward_id}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"Delete inward error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            conn.autocommit = True
            db_pool.return_connection(conn)


# ==================== TRANSFER ENDPOINTS ====================

@app.get("/api/transfer")
async def get_transfer_documents(request: Request, transfer_type: Optional[str] = None):
    """Get all transfer documents, optionally filtered by transfer_type"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        
        # Build query with optional transfer_type filter
        if transfer_type in ['simple', 'by_name']:
            query = """
                SELECT id, transfer_number, gp_number, sr_number, ms_party_id,
                       (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                       from_party, transfer_to, transfer_to_ms_party_id,
                       (SELECT name FROM liabilities WHERE id = transfer_to_ms_party_id) as transfer_to_ms_party_name,
                       vehicle_number, driver_name, total_quantity, transfer_type,
                       document_date, created_by, edited_by, edit_log_history, created_at
                FROM transfer_documents
                WHERE transfer_type = %s
                ORDER BY document_date DESC, transfer_number DESC
            """
            cursor.execute(query, (transfer_type,))
        else:
            query = """
                SELECT id, transfer_number, gp_number, sr_number, ms_party_id,
                       (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                       from_party, transfer_to, transfer_to_ms_party_id,
                       (SELECT name FROM liabilities WHERE id = transfer_to_ms_party_id) as transfer_to_ms_party_name,
                       vehicle_number, driver_name, total_quantity, transfer_type,
                       document_date, created_by, edited_by, edit_log_history, created_at
                FROM transfer_documents
                ORDER BY document_date DESC, transfer_number DESC
            """
            cursor.execute(query)
        
        documents = cursor.fetchall()
        
        for doc in documents:
            if doc['document_date']:
                doc['document_date'] = doc['document_date'].isoformat()
            if doc['created_at']:
                doc['created_at'] = doc['created_at'].isoformat()
            doc['total_quantity'] = float(doc['total_quantity'])
            # Ensure transfer_type is set (default to 'simple' for old records)
            if not doc.get('transfer_type'):
                doc['transfer_type'] = 'simple'
        
        cursor.close()
        return {"success": True, "documents": documents}
    except Exception as e:
        print(f"Get transfer documents error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/transfer/{transfer_id}")
async def get_transfer_document(transfer_id: int, request: Request):
    """Get a specific transfer document with items"""
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
            SELECT id, transfer_number, gp_number, sr_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   from_party, transfer_to, transfer_to_ms_party_id,
                   (SELECT name FROM liabilities WHERE id = transfer_to_ms_party_id) as transfer_to_ms_party_name,
                   transfer_type, vehicle_number, driver_name, total_quantity,
                   document_date, created_by, edited_by, edit_log_history, created_at
            FROM transfer_documents
            WHERE id = %s
        """, (transfer_id,))
        document = cursor.fetchone()
        
        if not document:
            cursor.close()
            raise HTTPException(status_code=404, detail="Document not found")
        
        cursor.execute("""
            SELECT item_name, measurement, quantity
            FROM transfer_items
            WHERE transfer_document_id = %s
            ORDER BY item_name, measurement
        """, (transfer_id,))
        items = cursor.fetchall()
        
        if document['document_date']:
            document['document_date'] = document['document_date'].isoformat()
        if document['created_at']:
            document['created_at'] = document['created_at'].isoformat()
        document['total_quantity'] = float(document['total_quantity'])
        
        for item in items:
            item['quantity'] = float(item['quantity'])
        
        document['items'] = items
        cursor.close()
        return {"success": True, "document": document}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get transfer document error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/api/transfer")
async def create_transfer(transfer_req: CreateTransferRequest, request: Request):
    """Create a new transfer document"""
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
        
        # Validate measurements and quantities
        for item in transfer_req.items:
            if item.measurement not in [15, 22]:
                raise HTTPException(status_code=400, detail=f"Invalid measurement: {item.measurement}")
            if item.quantity <= 0:
                raise HTTPException(status_code=400, detail=f"Quantity must be greater than 0 for {item.item_name} ({item.measurement})")
        
        # Check duplicates
        item_keys = [(item.item_name, item.measurement) for item in transfer_req.items]
        if len(item_keys) != len(set(item_keys)):
            raise HTTPException(status_code=400, detail="Duplicate item + measurement")
        
        # Get party name
        cursor.execute("SELECT name FROM liabilities WHERE id = %s", (transfer_req.ms_party_id,))
        party_result = cursor.fetchone()
        if not party_result:
            raise HTTPException(status_code=404, detail="MS Party not found")
        party_name = party_result.get('name')
        
        # Generate numbers - separate counters for By Name transfers
        if transfer_req.transfer_type == 'by_name':
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
        
        # Calculate total
        total_qty = sum(item.quantity for item in transfer_req.items)
        
        # Check stock availability
        items_dict = [{"item_name": item.item_name, "measurement": item.measurement, "quantity": item.quantity}
                     for item in transfer_req.items]
        
        # Validate By Name Transfer rules
        if transfer_req.transfer_type == 'by_name':
            if not transfer_req.transfer_to_ms_party_id:
                raise HTTPException(status_code=400, detail="Transfer To MS Party is required for By Name Transfer")
            if transfer_req.transfer_to_ms_party_id == transfer_req.ms_party_id:
                raise HTTPException(status_code=400, detail="Transfer To MS Party cannot be the same as source MS Party")
        
        # Insert document
        cursor.execute("""
            INSERT INTO transfer_documents 
            (transfer_number, gp_number, sr_number, ms_party_id, from_party,
             transfer_to, transfer_to_ms_party_id, transfer_type, vehicle_number, driver_name, total_quantity, document_date, created_by, edited_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
        """, (transfer_number_format, f"GP-{gp_num:06d}", sr_number_format,
              transfer_req.ms_party_id, transfer_req.from_party,
              transfer_req.transfer_to, transfer_req.transfer_to_ms_party_id, transfer_req.transfer_type,
              transfer_req.vehicle_number, transfer_req.driver_name,
              total_qty, transfer_req.document_date, transfer_req.created_by))
        
        document_id = cursor.lastrowid
        
        # Insert items
        for item in transfer_req.items:
            cursor.execute("""
                INSERT INTO transfer_items (transfer_document_id, item_name, measurement, quantity)
                VALUES (%s, %s, %s, %s)
            """, (document_id, item.item_name, item.measurement, item.quantity))
        
        # Update stock based on transfer type
        try:
            if transfer_req.transfer_type == 'by_name':
                # BN Transfer: Deduct from source, add to destination
                if not transfer_req.transfer_to_ms_party_id:
                    raise HTTPException(status_code=400, detail="Transfer To MS Party is required for By Name Transfer")
                from host.stock_manager import update_stock_for_transfer_bn
                update_stock_for_transfer_bn(transfer_req.ms_party_id, transfer_req.transfer_to_ms_party_id, items_dict)
            else:
                # Simple Transfer: Only deduct from source (no addition to destination)
                update_stock_for_transfer(transfer_req.ms_party_id, items_dict)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Create ledger entries based on transfer type
        # Format document date
        doc_date_str = transfer_req.document_date
        if isinstance(doc_date_str, str):
            try:
                doc_date = datetime.strptime(doc_date_str[:10], '%Y-%m-%d').date()
            except:
                doc_date = datetime.now().date()
        else:
            doc_date = doc_date_str if hasattr(doc_date_str, 'isoformat') else datetime.now().date()
        
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
                transfer_to_party_name = transfer_to_result.get('name') if transfer_to_result else "Unknown Party"
                raise HTTPException(status_code=500, detail=f"Ledger not found for party {transfer_to_party_name}")
            
            # Get transfer to party name for ledger entries
            cursor.execute("SELECT name FROM liabilities WHERE id = %s", (transfer_req.transfer_to_ms_party_id,))
            transfer_to_result = cursor.fetchone()
            transfer_to_party_name = transfer_to_result.get('name') if transfer_to_result else "Unknown Party"
            
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
        
        conn.commit()
        cursor.close()

        # Fetch created transfer summary for instant UI patching
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, transfer_number, gp_number, sr_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   from_party, transfer_to, transfer_to_ms_party_id,
                   (SELECT name FROM liabilities WHERE id = transfer_to_ms_party_id) as transfer_to_ms_party_name,
                   vehicle_number, driver_name, total_quantity, transfer_type,
                   document_date, created_by, edited_by, edit_log_history, created_at
            FROM transfer_documents
            WHERE id = %s
        """, (document_id,))
        created_doc = cursor.fetchone()
        cursor.close()

        if created_doc:
            if created_doc.get('document_date'):
                created_doc['document_date'] = created_doc['document_date'].isoformat()
            if created_doc.get('created_at'):
                created_doc['created_at'] = created_doc['created_at'].isoformat()
            created_doc['total_quantity'] = float(created_doc.get('total_quantity', 0))

        # Broadcast real-time change (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "transfer",
                "action": "created",
                "data": created_doc or {"id": document_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting transfer created: {e}")

        return {"success": True, "message": "Transfer document created successfully", "document_id": document_id, "document": created_doc}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"Create transfer error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            conn.autocommit = True
            db_pool.return_connection(conn)


@app.put("/api/transfer")
async def update_transfer(transfer_req: UpdateTransferRequest, request: Request):
    """Update a transfer document"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
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
        
        # Get existing document with all fields for edit log
        cursor.execute("""
            SELECT id, ms_party_id, from_party, transfer_to, transfer_to_ms_party_id, 
                   transfer_type, vehicle_number, driver_name, document_date, total_quantity, transfer_number
            FROM transfer_documents WHERE id = %s
        """, (transfer_req.transfer_id,))
        existing = cursor.fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Document not found")
        
        old_transfer_type = existing.get('transfer_type', 'simple')
        old_transfer_to_ms_party_id = existing.get('transfer_to_ms_party_id')
        old_transfer_number = existing.get('transfer_number')
        
        # Get old items
        cursor.execute("""
            SELECT item_name, measurement, quantity
            FROM transfer_items
            WHERE transfer_document_id = %s
        """, (transfer_req.transfer_id,))
        old_items = cursor.fetchall()
        
        # Get party names for edit log
        party_ids = {existing.get('ms_party_id'), transfer_req.ms_party_id}
        if existing.get('transfer_to_ms_party_id'):
            party_ids.add(existing.get('transfer_to_ms_party_id'))
        if transfer_req.transfer_to_ms_party_id:
            party_ids.add(transfer_req.transfer_to_ms_party_id)
        party_names = {}
        if party_ids:
            placeholders = ','.join(['%s'] * len(party_ids))
            cursor.execute(f"""
                SELECT id, name FROM liabilities WHERE id IN ({placeholders})
            """, tuple(party_ids))
            for row in cursor.fetchall():
                party_names[row['id']] = row['name']
        
        # Delete old ledger entries
        if old_transfer_number:
            delete_ledger_entries_by_transaction(conn, old_transfer_number)
        
        # Restore old stock based on old transfer type
        old_items_dict = [{"item_name": item['item_name'], "measurement": item['measurement'], "quantity": float(item['quantity'])}
                         for item in old_items]
        
        if old_transfer_type == 'by_name' and old_transfer_to_ms_party_id:
            # Reverse BN transfer: reverse both source and destination
            from host.stock_manager import update_stock_for_transfer_bn
            update_stock_for_transfer_bn(existing['ms_party_id'], old_transfer_to_ms_party_id, old_items_dict, reverse=True)
        else:
            # Reverse simple transfer: only reverse source
            update_stock_for_transfer(existing['ms_party_id'], old_items_dict, reverse=True)
        
        # Validate new items
        for item in transfer_req.items:
            if item.measurement not in [15, 22]:
                raise HTTPException(status_code=400, detail=f"Invalid measurement: {item.measurement}")
            if item.quantity <= 0:
                raise HTTPException(status_code=400, detail=f"Quantity must be greater than 0 for {item.item_name} ({item.measurement})")
        
        item_keys = [(item.item_name, item.measurement) for item in transfer_req.items]
        if len(item_keys) != len(set(item_keys)):
            raise HTTPException(status_code=400, detail="Duplicate item + measurement")
        
        total_qty = sum(item.quantity for item in transfer_req.items)
        
        # Validate By Name Transfer rules
        if transfer_req.transfer_type == 'by_name':
            if not transfer_req.transfer_to_ms_party_id:
                raise HTTPException(status_code=400, detail="Transfer To MS Party is required for By Name Transfer")
            if transfer_req.transfer_to_ms_party_id == transfer_req.ms_party_id:
                raise HTTPException(status_code=400, detail="Transfer To MS Party cannot be the same as source MS Party")
        
        # Prepare new document data for edit log
        new_doc = {
            'ms_party_id': transfer_req.ms_party_id,
            'from_party': transfer_req.from_party or '',
            'transfer_to': transfer_req.transfer_to or '',
            'transfer_to_ms_party_id': transfer_req.transfer_to_ms_party_id,
            'transfer_type': transfer_req.transfer_type,
            'vehicle_number': transfer_req.vehicle_number or '',
            'driver_name': transfer_req.driver_name or '',
            'document_date': transfer_req.document_date,
            'total_quantity': total_qty
        }
        
        # Prepare new items for edit log
        new_items = [
            {'item_name': item.item_name, 'measurement': item.measurement, 'quantity': item.quantity}
            for item in transfer_req.items
        ]
        
        # Generate edit log
        from host.edit_log_generator import generate_transfer_edit_log
        edit_log = generate_transfer_edit_log(existing, new_doc, old_items, new_items, party_names)
        
        # Update document (set edited_by and edit_log_history on update, never change created_by)
        cursor.execute("""
            UPDATE transfer_documents
            SET ms_party_id = %s, from_party = %s, transfer_to = %s,
                transfer_to_ms_party_id = %s, transfer_type = %s,
                vehicle_number = %s, driver_name = %s, total_quantity = %s, document_date = %s, 
                edited_by = %s, edit_log_history = %s
            WHERE id = %s
        """, (transfer_req.ms_party_id, transfer_req.from_party, transfer_req.transfer_to,
              transfer_req.transfer_to_ms_party_id, transfer_req.transfer_type,
              transfer_req.vehicle_number, transfer_req.driver_name, total_qty,
              transfer_req.document_date, edited_by, edit_log, transfer_req.transfer_id))
        
        # Delete old items
        cursor.execute("DELETE FROM transfer_items WHERE transfer_document_id = %s", (transfer_req.transfer_id,))
        
        # Insert new items
        for item in transfer_req.items:
            cursor.execute("""
                INSERT INTO transfer_items (transfer_document_id, item_name, measurement, quantity)
                VALUES (%s, %s, %s, %s)
            """, (transfer_req.transfer_id, item.item_name, item.measurement, item.quantity))
        
        # Update stock based on new transfer type
        new_items_dict = [{"item_name": item.item_name, "measurement": item.measurement, "quantity": item.quantity}
                         for item in transfer_req.items]
        try:
            if transfer_req.transfer_type == 'by_name':
                # BN Transfer: Deduct from source, add to destination
                if not transfer_req.transfer_to_ms_party_id:
                    raise HTTPException(status_code=400, detail="Transfer To MS Party is required for By Name Transfer")
                from host.stock_manager import update_stock_for_transfer_bn
                update_stock_for_transfer_bn(transfer_req.ms_party_id, transfer_req.transfer_to_ms_party_id, new_items_dict)
            else:
                # Simple Transfer: Only deduct from source (no addition to destination)
                update_stock_for_transfer(transfer_req.ms_party_id, new_items_dict)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Get party name for ledger entries
        cursor.execute("SELECT name FROM liabilities WHERE id = %s", (transfer_req.ms_party_id,))
        party_result = cursor.fetchone()
        party_name = party_result.get('name') if party_result else "Unknown Party"
        
        # Format document date
        doc_date_str = transfer_req.document_date
        if isinstance(doc_date_str, str):
            try:
                doc_date = datetime.strptime(doc_date_str[:10], '%Y-%m-%d').date()
            except:
                doc_date = datetime.now().date()
        else:
            doc_date = doc_date_str if hasattr(doc_date_str, 'isoformat') else datetime.now().date()
        
        # Create new ledger entries based on transfer type
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
                transfer_to_party_name = transfer_to_result.get('name') if transfer_to_result else "Unknown Party"
                raise HTTPException(status_code=500, detail=f"Ledger not found for party {transfer_to_party_name}")
            
            # Get transfer to party name for ledger entries
            cursor.execute("SELECT name FROM liabilities WHERE id = %s", (transfer_req.transfer_to_ms_party_id,))
            transfer_to_result = cursor.fetchone()
            transfer_to_party_name = transfer_to_result.get('name') if transfer_to_result else "Unknown Party"
            
            # Create ledger entries for each item
            for item in transfer_req.items:
                qty_15 = item.quantity if item.measurement == 15 else 0.0
                qty_22 = item.quantity if item.measurement == 22 else 0.0
                total_qty = item.quantity
                
                # Party A Ledger Entry: Debit
                create_ledger_entry(
                    conn, party_a_ledger_id, doc_date.isoformat(),
                    "Transfer By Name #", old_transfer_number,
                    transfer_to_party_name,  # Particulars
                    "Stock transfer by name",  # Description
                    item.item_name, qty_15, qty_22,
                    total_qty, 0.0  # Debit, no credit
                )
                
                # Transfer To Party Ledger Entry: Credit
                create_ledger_entry(
                    conn, transfer_to_ledger_id, doc_date.isoformat(),
                    "Transfer By Name #", old_transfer_number,
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
                    "Transfer #", old_transfer_number,
                    party_name,  # Particulars
                    f"Stock transfer to {transfer_req.transfer_to or 'N/A'}",  # Description
                    item.item_name, qty_15, qty_22,
                    0.0, total_qty  # No debit, credit
                )
                
                # Party A Ledger Entry: Debit
                create_ledger_entry(
                    conn, party_ledger_id, doc_date.isoformat(),
                    "Transfer #", old_transfer_number,
                    "UNIVERSAL DYEING",  # Particulars
                    f"Stock transfer to {transfer_req.transfer_to or 'N/A'}",  # Description
                    item.item_name, qty_15, qty_22,
                    total_qty, 0.0  # Debit, no credit
                )
        
        conn.commit()
        cursor.close()

        # Fetch updated transfer summary for instant UI patching
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, transfer_number, gp_number, sr_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   from_party, transfer_to, transfer_to_ms_party_id,
                   (SELECT name FROM liabilities WHERE id = transfer_to_ms_party_id) as transfer_to_ms_party_name,
                   vehicle_number, driver_name, total_quantity, transfer_type,
                   document_date, created_by, edited_by, edit_log_history, created_at
            FROM transfer_documents
            WHERE id = %s
        """, (transfer_req.transfer_id,))
        updated_doc = cursor.fetchone()
        cursor.close()

        if updated_doc:
            if updated_doc.get('document_date'):
                updated_doc['document_date'] = updated_doc['document_date'].isoformat()
            if updated_doc.get('created_at'):
                updated_doc['created_at'] = updated_doc['created_at'].isoformat()
            updated_doc['total_quantity'] = float(updated_doc.get('total_quantity', 0))

        # Broadcast real-time change (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "transfer",
                "action": "updated",
                "data": updated_doc or {"id": transfer_req.transfer_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting transfer updated: {e}")

        return {"success": True, "message": "Transfer document updated successfully", "document": updated_doc}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"Update transfer error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            conn.autocommit = True
            db_pool.return_connection(conn)


@app.delete("/api/transfer/{transfer_id}")
async def delete_transfer(transfer_id: int, request: Request):
    """Delete a transfer document"""
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
        
        cursor.execute("SELECT id, ms_party_id, transfer_type, transfer_to_ms_party_id, transfer_number FROM transfer_documents WHERE id = %s", (transfer_id,))
        document = cursor.fetchone()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        transfer_type = document.get('transfer_type', 'simple')
        transfer_to_ms_party_id = document.get('transfer_to_ms_party_id')
        transfer_number = document.get('transfer_number')
        
        cursor.execute("""
            SELECT item_name, measurement, quantity
            FROM transfer_items
            WHERE transfer_document_id = %s
        """, (transfer_id,))
        items = cursor.fetchall()
        
        # Delete ledger entries for this transaction
        if transfer_number:
            delete_ledger_entries_by_transaction(conn, transfer_number)
        
        # Restore stock based on transfer type
        items_dict = [{"item_name": item['item_name'], "measurement": item['measurement'], "quantity": float(item['quantity'])}
                     for item in items]
        
        if transfer_type == 'by_name' and transfer_to_ms_party_id:
            # Reverse BN transfer: reverse both source and destination
            from host.stock_manager import update_stock_for_transfer_bn
            update_stock_for_transfer_bn(document['ms_party_id'], transfer_to_ms_party_id, items_dict, reverse=True)
        else:
            # Reverse simple transfer: only reverse source
            update_stock_for_transfer(document['ms_party_id'], items_dict, reverse=True)
        
        cursor.execute("DELETE FROM transfer_documents WHERE id = %s", (transfer_id,))
        
        conn.commit()
        cursor.close()

        # Broadcast real-time change (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "transfer",
                "action": "deleted",
                "data": {"id": transfer_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting transfer deleted: {e}")

        return {"success": True, "message": "Transfer document deleted successfully", "document_id": transfer_id}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"Delete transfer error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            conn.autocommit = True
            db_pool.return_connection(conn)


# ==================== OUTWARD ENDPOINTS ====================

@app.get("/api/outward")
async def get_outward_documents(request: Request):
    """Get all outward documents"""
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
            SELECT id, outward_number, gp_number, sr_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   from_party, outward_to, vehicle_number, driver_name, total_quantity,
                   document_date, created_by, edited_by, edit_log_history, created_at
            FROM outward_documents
            ORDER BY document_date DESC, outward_number DESC
        """)
        documents = cursor.fetchall()
        
        for doc in documents:
            if doc['document_date']:
                doc['document_date'] = doc['document_date'].isoformat()
            if doc['created_at']:
                doc['created_at'] = doc['created_at'].isoformat()
            doc['total_quantity'] = float(doc['total_quantity'])
        
        cursor.close()
        return {"success": True, "documents": documents}
    except Exception as e:
        print(f"Get outward documents error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/outward/{outward_id}")
async def get_outward_document(outward_id: int, request: Request):
    """Get a specific outward document with items"""
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
            SELECT id, outward_number, gp_number, sr_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   from_party, outward_to, vehicle_number, driver_name, total_quantity,
                   document_date, created_by, edited_by, edit_log_history, created_at
            FROM outward_documents
            WHERE id = %s
        """, (outward_id,))
        document = cursor.fetchone()
        
        if not document:
            cursor.close()
            raise HTTPException(status_code=404, detail="Document not found")
        
        cursor.execute("""
            SELECT item_name, measurement, quantity
            FROM outward_items
            WHERE outward_document_id = %s
            ORDER BY item_name, measurement
        """, (outward_id,))
        items = cursor.fetchall()
        
        if document['document_date']:
            document['document_date'] = document['document_date'].isoformat()
        if document['created_at']:
            document['created_at'] = document['created_at'].isoformat()
        document['total_quantity'] = float(document['total_quantity'])
        
        for item in items:
            item['quantity'] = float(item['quantity'])
        
        document['items'] = items
        cursor.close()
        return {"success": True, "document": document}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get outward document error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/api/outward")
async def create_outward(outward_req: CreateOutwardRequest, request: Request):
    """Create a new outward document"""
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
        
        # Validate measurements and quantities
        for item in outward_req.items:
            if item.measurement not in [15, 22]:
                raise HTTPException(status_code=400, detail=f"Invalid measurement: {item.measurement}")
            if item.quantity <= 0:
                raise HTTPException(status_code=400, detail=f"Quantity must be greater than 0 for {item.item_name} ({item.measurement})")
        
        item_keys = [(item.item_name, item.measurement) for item in outward_req.items]
        if len(item_keys) != len(set(item_keys)):
            raise HTTPException(status_code=400, detail="Duplicate item + measurement")
        
        cursor.execute("SELECT name FROM liabilities WHERE id = %s", (outward_req.ms_party_id,))
        party_result = cursor.fetchone()
        if not party_result:
            raise HTTPException(status_code=404, detail="MS Party not found")
        party_name = party_result.get('name')
        
        outward_num = get_next_number("OUTWARD")
        if outward_num is None:
            raise HTTPException(status_code=500, detail="Failed to generate outward number")
        
        gp_num = outward_num
        sr_num = get_next_number("SR", party_name)
        if sr_num is None:
            raise HTTPException(status_code=500, detail="Failed to generate SR number")
        
        total_qty = sum(item.quantity for item in outward_req.items)
        
        items_dict = [{"item_name": item.item_name, "measurement": item.measurement, "quantity": item.quantity}
                     for item in outward_req.items]
        
        cursor.execute("""
            INSERT INTO outward_documents 
            (outward_number, gp_number, sr_number, ms_party_id, from_party,
             outward_to, vehicle_number, driver_name, total_quantity, document_date, created_by, edited_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
        """, (f"OUT-{outward_num:06d}", f"GP-{gp_num:06d}", f"SR-{sr_num:06d}",
              outward_req.ms_party_id, outward_req.from_party,
              outward_req.outward_to, outward_req.vehicle_number, outward_req.driver_name,
              total_qty, outward_req.document_date, outward_req.created_by))
        
        document_id = cursor.lastrowid
        
        for item in outward_req.items:
            cursor.execute("""
                INSERT INTO outward_items (outward_document_id, item_name, measurement, quantity)
                VALUES (%s, %s, %s, %s)
            """, (document_id, item.item_name, item.measurement, item.quantity))
        
        try:
            update_stock_for_outward(outward_req.ms_party_id, items_dict)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Get party name for ledger entries
        cursor.execute("SELECT name FROM liabilities WHERE id = %s", (outward_req.ms_party_id,))
        party_name_result = cursor.fetchone()
        party_name = party_name_result.get('name') if party_name_result else "Unknown Party"
        
        # Get ledger IDs
        ud_ledger_id = get_ud_ledger_id(conn)
        party_ledger_id = get_party_ledger_id(conn, outward_req.ms_party_id)
        
        if not ud_ledger_id:
            raise HTTPException(status_code=500, detail="UD Ledger not found")
        if not party_ledger_id:
            raise HTTPException(status_code=500, detail=f"Ledger not found for party {party_name}")
        
        # Format document date
        doc_date_str = outward_req.document_date
        if isinstance(doc_date_str, str):
            try:
                doc_date = datetime.strptime(doc_date_str[:10], '%Y-%m-%d').date()
            except:
                doc_date = datetime.now().date()
        else:
            doc_date = doc_date_str if hasattr(doc_date_str, 'isoformat') else datetime.now().date()
        
        outward_number = f"OUT-{outward_num:06d}"
        
        # Create ledger entries for each item
        for item in outward_req.items:
            qty_15 = item.quantity if item.measurement == 15 else 0.0
            qty_22 = item.quantity if item.measurement == 22 else 0.0
            total_qty = item.quantity
            
            # UD Ledger Entry: Credit
            create_ledger_entry(
                conn, ud_ledger_id, doc_date.isoformat(),
                "Outward #", outward_number,
                party_name,  # Particulars
                f"Stock outward to {outward_req.outward_to or 'N/A'}",  # Description
                item.item_name, qty_15, qty_22,
                0.0, total_qty  # No debit, credit
            )
            
            # Party Ledger Entry: Debit
            create_ledger_entry(
                conn, party_ledger_id, doc_date.isoformat(),
                "Outward #", outward_number,
                "UNIVERSAL DYEING",  # Particulars
                f"Stock outward to {outward_req.outward_to or 'N/A'}",  # Description
                item.item_name, qty_15, qty_22,
                total_qty, 0.0  # Debit, no credit
            )
        
        conn.commit()
        cursor.close()

        # Fetch created outward summary for instant UI patching
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, outward_number, gp_number, sr_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   from_party, outward_to, vehicle_number, driver_name, total_quantity,
                   document_date, created_by, edited_by, edit_log_history, created_at
            FROM outward_documents
            WHERE id = %s
        """, (document_id,))
        created_doc = cursor.fetchone()
        cursor.close()

        if created_doc:
            if created_doc.get('document_date'):
                created_doc['document_date'] = created_doc['document_date'].isoformat()
            if created_doc.get('created_at'):
                created_doc['created_at'] = created_doc['created_at'].isoformat()
            created_doc['total_quantity'] = float(created_doc.get('total_quantity', 0))

        # Broadcast real-time change (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "outward",
                "action": "created",
                "data": created_doc or {"id": document_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting outward created: {e}")

        return {"success": True, "message": "Outward document created successfully", "document_id": document_id, "document": created_doc}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"Create outward error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            conn.autocommit = True
            db_pool.return_connection(conn)


@app.put("/api/outward")
async def update_outward(outward_req: UpdateOutwardRequest, request: Request):
    """Update an outward document"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
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
        
        # Get existing document with all fields for edit log
        cursor.execute("""
            SELECT id, ms_party_id, from_party, outward_to, vehicle_number, 
                   driver_name, document_date, total_quantity, outward_number
            FROM outward_documents WHERE id = %s
        """, (outward_req.outward_id,))
        existing = cursor.fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Document not found")
        
        old_outward_number = existing.get('outward_number')
        old_ms_party_id = existing.get('ms_party_id')
        
        cursor.execute("""
            SELECT item_name, measurement, quantity
            FROM outward_items
            WHERE outward_document_id = %s
        """, (outward_req.outward_id,))
        old_items = cursor.fetchall()
        
        # Get party names for edit log
        party_ids = {existing.get('ms_party_id'), outward_req.ms_party_id}
        party_names = {}
        if party_ids:
            placeholders = ','.join(['%s'] * len(party_ids))
            cursor.execute(f"""
                SELECT id, name FROM liabilities WHERE id IN ({placeholders})
            """, tuple(party_ids))
            for row in cursor.fetchall():
                party_names[row['id']] = row['name']
        
        # Reverse old stock within the same transaction
        for item in old_items:
            item_name = item['item_name']
            measurement = item['measurement']
            quantity = -float(item['quantity'])  # Negative because we're reversing
            
            # Check if stock record exists before reversing
            cursor.execute("""
                SELECT id FROM stock 
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (old_ms_party_id, item_name, measurement))
            
            stock_result = cursor.fetchone()
            if not stock_result:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot reverse stock: Stock record not found for {item_name} ({measurement})"
                )
            
            # Update stock - subtract from total_outward
            cursor.execute("""
                UPDATE stock SET total_outward = total_outward + %s
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (quantity, old_ms_party_id, item_name, measurement))
            
            # Verify the update affected a row
            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to reverse stock for {item_name} ({measurement})"
                )
        
        # Delete old ledger entries
        if old_outward_number:
            delete_ledger_entries_by_transaction(conn, old_outward_number)
        
        for item in outward_req.items:
            if item.measurement not in [15, 22]:
                raise HTTPException(status_code=400, detail=f"Invalid measurement: {item.measurement}")
            if item.quantity <= 0:
                raise HTTPException(status_code=400, detail=f"Quantity must be greater than 0 for {item.item_name} ({item.measurement})")
        
        item_keys = [(item.item_name, item.measurement) for item in outward_req.items]
        if len(item_keys) != len(set(item_keys)):
            raise HTTPException(status_code=400, detail="Duplicate item + measurement")
        
        total_qty = sum(item.quantity for item in outward_req.items)
        
        # Prepare new document data for edit log
        new_doc = {
            'ms_party_id': outward_req.ms_party_id,
            'from_party': outward_req.from_party or '',
            'outward_to': outward_req.outward_to or '',
            'vehicle_number': outward_req.vehicle_number or '',
            'driver_name': outward_req.driver_name or '',
            'document_date': outward_req.document_date,
            'total_quantity': total_qty
        }
        
        # Prepare new items for edit log
        new_items = [
            {'item_name': item.item_name, 'measurement': item.measurement, 'quantity': item.quantity}
            for item in outward_req.items
        ]
        
        # Generate edit log
        from host.edit_log_generator import generate_outward_edit_log
        edit_log = generate_outward_edit_log(existing, new_doc, old_items, new_items, party_names)
        
        cursor.execute("""
            UPDATE outward_documents
            SET ms_party_id = %s, from_party = %s, outward_to = %s,
                vehicle_number = %s, driver_name = %s, total_quantity = %s, document_date = %s, 
                edited_by = %s, edit_log_history = %s
            WHERE id = %s
        """, (outward_req.ms_party_id, outward_req.from_party, outward_req.outward_to,
              outward_req.vehicle_number, outward_req.driver_name, total_qty,
              outward_req.document_date, edited_by, edit_log, outward_req.outward_id))
        
        cursor.execute("DELETE FROM outward_items WHERE outward_document_id = %s", (outward_req.outward_id,))
        
        for item in outward_req.items:
            cursor.execute("""
                INSERT INTO outward_items (outward_document_id, item_name, measurement, quantity)
                VALUES (%s, %s, %s, %s)
            """, (outward_req.outward_id, item.item_name, item.measurement, item.quantity))
        
        # Update stock with new items within the same transaction
        for item in outward_req.items:
            item_name = item.item_name
            measurement = item.measurement
            quantity = item.quantity
            
            # Check if stock record exists and has sufficient stock
            cursor.execute("""
                SELECT id, remaining_stock FROM stock 
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (outward_req.ms_party_id, item_name, measurement))
            
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=400, detail=f"Stock not found for {item_name} ({measurement})")
            
            current_stock = float(result.get('remaining_stock', 0))
            if current_stock < quantity:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient stock for {item_name} ({measurement}). Available: {current_stock}, Required: {quantity}"
                )
            
            # Update stock - add to total_outward
            cursor.execute("""
                UPDATE stock SET total_outward = total_outward + %s
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (quantity, outward_req.ms_party_id, item_name, measurement))
            
            # Verify the update affected a row
            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to update stock for {item_name} ({measurement})"
                )
        
        # Get updated outward_number for new ledger entries
        cursor.execute("SELECT outward_number FROM outward_documents WHERE id = %s", (outward_req.outward_id,))
        updated_doc = cursor.fetchone()
        new_outward_number = updated_doc.get('outward_number') if updated_doc else None
        
        # Get party name for ledger entries
        cursor.execute("SELECT name FROM liabilities WHERE id = %s", (outward_req.ms_party_id,))
        party_name_result = cursor.fetchone()
        party_name = party_name_result.get('name') if party_name_result else "Unknown Party"
        
        # Get ledger IDs
        ud_ledger_id = get_ud_ledger_id(conn)
        party_ledger_id = get_party_ledger_id(conn, outward_req.ms_party_id)
        
        if not ud_ledger_id:
            raise HTTPException(status_code=500, detail="UD Ledger not found")
        if not party_ledger_id:
            raise HTTPException(status_code=500, detail=f"Ledger not found for party ID {outward_req.ms_party_id}")
        
        if new_outward_number:
            # Format document date
            doc_date_str = outward_req.document_date
            if isinstance(doc_date_str, str):
                try:
                    doc_date = datetime.strptime(doc_date_str[:10], '%Y-%m-%d').date()
                except:
                    doc_date = datetime.now().date()
            else:
                doc_date = doc_date_str if hasattr(doc_date_str, 'isoformat') else datetime.now().date()
            
            # Create new ledger entries for each item
            for item in outward_req.items:
                qty_15 = item.quantity if item.measurement == 15 else 0.0
                qty_22 = item.quantity if item.measurement == 22 else 0.0
                total_qty = item.quantity
                
                # UD Ledger Entry: Credit
                create_ledger_entry(
                    conn, ud_ledger_id, doc_date.isoformat(),
                    "Outward #", new_outward_number,
                    party_name,  # Particulars
                    f"Stock outward to {outward_req.outward_to or 'N/A'}",  # Description
                    item.item_name, qty_15, qty_22,
                    0.0, total_qty  # No debit, credit
                )
                
                # Party Ledger Entry: Debit
                create_ledger_entry(
                    conn, party_ledger_id, doc_date.isoformat(),
                    "Outward #", new_outward_number,
                    "UNIVERSAL DYEING",  # Particulars
                    f"Stock outward to {outward_req.outward_to or 'N/A'}",  # Description
                    item.item_name, qty_15, qty_22,
                    total_qty, 0.0  # Debit, no credit
                )
        
        conn.commit()
        cursor.close()

        # Fetch updated outward summary for instant UI patching
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, outward_number, gp_number, sr_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   from_party, outward_to, vehicle_number, driver_name, total_quantity,
                   document_date, created_by, edited_by, edit_log_history, created_at
            FROM outward_documents
            WHERE id = %s
        """, (outward_req.outward_id,))
        updated_doc = cursor.fetchone()
        cursor.close()

        if updated_doc:
            if updated_doc.get('document_date'):
                updated_doc['document_date'] = updated_doc['document_date'].isoformat()
            if updated_doc.get('created_at'):
                updated_doc['created_at'] = updated_doc['created_at'].isoformat()
            updated_doc['total_quantity'] = float(updated_doc.get('total_quantity', 0))

        # Broadcast real-time change (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "outward",
                "action": "updated",
                "data": updated_doc or {"id": outward_req.outward_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting outward updated: {e}")

        return {"success": True, "message": "Outward document updated successfully", "document": updated_doc}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Update outward error: {e}")
        print(f"Traceback: {error_details}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            conn.autocommit = True
            db_pool.return_connection(conn)


@app.delete("/api/outward/{outward_id}")
async def delete_outward(outward_id: int, request: Request):
    """Delete an outward document"""
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
        
        cursor.execute("SELECT id, ms_party_id, outward_number FROM outward_documents WHERE id = %s", (outward_id,))
        document = cursor.fetchone()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        outward_number = document.get('outward_number')
        
        # Check if outward is invoiced - prevent deletion if it is
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM invoice_items 
            WHERE outward_document_id = %s
        """, (outward_id,))
        invoiced_result = cursor.fetchone()
        if invoiced_result and invoiced_result['count'] > 0:
            conn.rollback()
            cursor.close()
            raise HTTPException(
                status_code=400,
                detail="Cannot delete outward document that is part of an invoice. Please delete the invoice first."
            )
        
        cursor.execute("""
            SELECT item_name, measurement, quantity
            FROM outward_items
            WHERE outward_document_id = %s
        """, (outward_id,))
        items = cursor.fetchall()
        
        update_stock_for_outward(document['ms_party_id'],
                                [{"item_name": item['item_name'], "measurement": item['measurement'], "quantity": float(item['quantity'])}
                                 for item in items], reverse=True)
        
        # Delete ledger entries for this transaction
        if outward_number:
            delete_ledger_entries_by_transaction(conn, outward_number)
        
        cursor.execute("DELETE FROM outward_documents WHERE id = %s", (outward_id,))
        
        conn.commit()
        cursor.close()

        # Broadcast real-time change (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "outward",
                "action": "deleted",
                "data": {"id": outward_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting outward deleted: {e}")

        return {"success": True, "message": "Outward document deleted successfully", "document_id": outward_id}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"Delete outward error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            conn.autocommit = True
            db_pool.return_connection(conn)

