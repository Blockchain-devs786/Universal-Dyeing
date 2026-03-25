"""Stock Management Helper Functions"""

from typing import List, Dict, Optional
from host.db_pool import db_pool
from datetime import datetime


def get_next_number(counter_type: str, party_name: Optional[str] = None) -> int:
    """Get next number for a counter type"""
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        
        # Build query based on whether party_name is needed
        if party_name:
            cursor.execute("""
                SELECT counter_value FROM auto_numbering 
                WHERE counter_type = %s AND party_name = %s
            """, (counter_type, party_name))
        else:
            cursor.execute("""
                SELECT counter_value FROM auto_numbering 
                WHERE counter_type = %s AND party_name IS NULL
            """, (counter_type,))
        
        result = cursor.fetchone()
        
        if result:
            current_value = result[0]
            new_value = current_value + 1
            if party_name:
                cursor.execute("""
                    UPDATE auto_numbering SET counter_value = %s 
                    WHERE counter_type = %s AND party_name = %s
                """, (new_value, counter_type, party_name))
            else:
                cursor.execute("""
                    UPDATE auto_numbering SET counter_value = %s 
                    WHERE counter_type = %s AND party_name IS NULL
                """, (new_value, counter_type))
        else:
            # Create new counter
            new_value = 1
            cursor.execute("""
                INSERT INTO auto_numbering (counter_type, counter_value, party_name)
                VALUES (%s, %s, %s)
            """, (counter_type, new_value, party_name))
        
        conn.commit()
        cursor.close()
        return new_value
    except Exception as e:
        print(f"Error getting next number: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            db_pool.return_connection(conn)


def update_stock_for_inward(ms_party_id: int, items: List[Dict], reverse: bool = False):
    """Update stock for inward items"""
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        for item in items:
            item_name = item['item_name']
            measurement = item['measurement']
            quantity = item['quantity']
            
            if reverse:
                quantity = -quantity
            
            # Check if stock record exists
            cursor.execute("""
                SELECT id FROM stock 
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (ms_party_id, item_name, measurement))
            
            result = cursor.fetchone()
            
            if result:
                # Update existing stock
                cursor.execute("""
                    UPDATE stock SET total_inward = total_inward + %s
                    WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
                """, (quantity, ms_party_id, item_name, measurement))
            else:
                # Create new stock record
                cursor.execute("""
                    INSERT INTO stock (ms_party_id, item_name, measurement, total_inward)
                    VALUES (%s, %s, %s, %s)
                """, (ms_party_id, item_name, measurement, quantity))
        
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error updating stock for inward: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            db_pool.return_connection(conn)


def update_stock_for_transfer(ms_party_id: int, items: List[Dict], reverse: bool = False):
    """Update stock for simple transfer items (deducts from stock only, no addition to destination)
    
    Simple Transfer Rule:
    - Deduct from owner stock only (total_transfer)
    - Do NOT add to any other party stock
    - No BN tracking involved
    """
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        for item in items:
            item_name = item['item_name']
            measurement = item['measurement']
            quantity = item['quantity']
            
            if reverse:
                quantity = -quantity
            
            # Check if stock record exists
            cursor.execute("""
                SELECT id, remaining_stock FROM stock 
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (ms_party_id, item_name, measurement))
            
            result = cursor.fetchone()
            
            if not result:
                raise Exception(f"Stock not found for {item_name} ({measurement})")
            
            # Check if stock would go negative
            current_stock = float(result[1])
            if not reverse and current_stock < quantity:
                raise Exception(f"Insufficient stock for {item_name} ({measurement}). Available: {current_stock}, Required: {quantity}")
            
            # Update stock - simple transfer only deducts (total_transfer)
            cursor.execute("""
                UPDATE stock SET total_transfer = total_transfer + %s
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (quantity, ms_party_id, item_name, measurement))
        
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error updating stock for transfer: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            db_pool.return_connection(conn)


def update_stock_for_transfer_bn(source_party_id: int, dest_party_id: int, items: List[Dict], reverse: bool = False):
    """Update stock for Transfer By Name (BN) - ownership changes
    
    BN Transfer Rule:
    - Deduct from source party (transfer_bn_out)
    - Add to destination party (transfer_bn_in)
    - Ownership shifts from source to destination
    """
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        for item in items:
            item_name = item['item_name']
            measurement = item['measurement']
            quantity = item['quantity']
            
            if reverse:
                quantity = -quantity
            
            # Update source party stock (deduct via transfer_bn_out)
            cursor.execute("""
                SELECT id, remaining_stock FROM stock 
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (source_party_id, item_name, measurement))
            
            source_result = cursor.fetchone()
            
            if not source_result:
                raise Exception(f"Stock not found for source party {source_party_id}, item {item_name} ({measurement})")
            
            # Check if source stock would go negative
            current_stock = float(source_result[1])
            if not reverse and current_stock < quantity:
                raise Exception(f"Insufficient stock for {item_name} ({measurement}). Available: {current_stock}, Required: {quantity}")
            
            # Deduct from source (transfer_bn_out)
            cursor.execute("""
                UPDATE stock SET transfer_bn_out = transfer_bn_out + %s
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (quantity, source_party_id, item_name, measurement))
            
            # Add to destination party (transfer_bn_in)
            # Check if destination stock record exists
            cursor.execute("""
                SELECT id FROM stock 
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (dest_party_id, item_name, measurement))
            
            dest_result = cursor.fetchone()
            
            if dest_result:
                # Update existing stock
                cursor.execute("""
                    UPDATE stock SET transfer_bn_in = transfer_bn_in + %s
                    WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
                """, (quantity, dest_party_id, item_name, measurement))
            else:
                # Create new stock record for destination (with zero inward, but BN in)
                cursor.execute("""
                    INSERT INTO stock (ms_party_id, item_name, measurement, transfer_bn_in)
                    VALUES (%s, %s, %s, %s)
                """, (dest_party_id, item_name, measurement, quantity))
        
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error updating stock for BN transfer: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            db_pool.return_connection(conn)


def update_stock_for_outward(ms_party_id: int, items: List[Dict], reverse: bool = False):
    """Update stock for outward items (deducts from stock)"""
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        for item in items:
            item_name = item['item_name']
            measurement = item['measurement']
            quantity = item['quantity']
            
            if reverse:
                quantity = -quantity
            
            # Check if stock record exists
            cursor.execute("""
                SELECT id, remaining_stock FROM stock 
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (ms_party_id, item_name, measurement))
            
            result = cursor.fetchone()
            
            if not result:
                raise Exception(f"Stock not found for {item_name} ({measurement})")
            
            # Check if stock would go negative
            current_stock = float(result[1])
            if not reverse and current_stock < quantity:
                raise Exception(f"Insufficient stock for {item_name} ({measurement}). Available: {current_stock}, Required: {quantity}")
            
            # Update stock
            cursor.execute("""
                UPDATE stock SET total_outward = total_outward + %s
                WHERE ms_party_id = %s AND item_name = %s AND measurement = %s
            """, (quantity, ms_party_id, item_name, measurement))
        
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error updating stock for outward: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            db_pool.return_connection(conn)


def get_stock_for_party(ms_party_id: int) -> List[Dict]:
    """Get stock for a specific MS Party
    
    Filters out items where all quantity columns are 0:
    - total_inward
    - total_transfer
    - transfer_bn_in
    - transfer_bn_out
    - total_outward
    - remaining_stock
    """
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT item_name, measurement, total_inward, total_transfer, 
                   transfer_bn_in, transfer_bn_out, total_outward, remaining_stock
            FROM stock
            WHERE ms_party_id = %s
            ORDER BY item_name, measurement
        """, (ms_party_id,))
        
        stock = cursor.fetchall()
        
        # Convert decimal to float and filter out items with all zeros
        filtered_stock = []
        for item in stock:
            total_inward = float(item.get('total_inward', 0))
            total_transfer = float(item.get('total_transfer', 0))
            transfer_bn_in = float(item.get('transfer_bn_in', 0))
            transfer_bn_out = float(item.get('transfer_bn_out', 0))
            total_outward = float(item.get('total_outward', 0))
            remaining_stock = float(item.get('remaining_stock', 0))
            
            # Only include items that have at least one non-zero quantity
            if (total_inward != 0 or total_transfer != 0 or transfer_bn_in != 0 or 
                transfer_bn_out != 0 or total_outward != 0 or remaining_stock != 0):
                item['total_inward'] = total_inward
                item['total_transfer'] = total_transfer
                item['transfer_bn_in'] = transfer_bn_in
                item['transfer_bn_out'] = transfer_bn_out
                item['total_outward'] = total_outward
                item['remaining_stock'] = remaining_stock
                filtered_stock.append(item)
        
        cursor.close()
        return filtered_stock
    except Exception as e:
        print(f"Error getting stock: {e}")
        return []
    finally:
        if conn:
            db_pool.return_connection(conn)


def get_parties_with_stock() -> List[Dict]:
    """Get list of MS Parties that have stock"""
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT DISTINCT p.id, p.name
            FROM liabilities p
            INNER JOIN stock s ON p.id = s.ms_party_id
            WHERE s.remaining_stock > 0
            ORDER BY p.name
        """)
        
        parties = cursor.fetchall()
        cursor.close()
        return parties
    except Exception as e:
        print(f"Error getting parties with stock: {e}")
        return []
    finally:
        if conn:
            db_pool.return_connection(conn)


def get_ud_ledger_id(conn) -> Optional[int]:
    """Get the UD ledger ID"""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM stock_ledgers WHERE is_ud_ledger = TRUE LIMIT 1")
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()


def get_party_ledger_id(conn, party_id: int) -> Optional[int]:
    """Get the ledger ID for a specific party"""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM stock_ledgers WHERE party_id = %s LIMIT 1", (party_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()


def get_last_balance(conn, ledger_id: int) -> float:
    """Get the last balance for a ledger"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT balance FROM stock_ledger_entries
            WHERE ledger_id = %s
            ORDER BY entry_date DESC, id DESC
            LIMIT 1
        """, (ledger_id,))
        result = cursor.fetchone()
        return float(result[0]) if result and result[0] is not None else 0.0
    finally:
        cursor.close()


def create_ledger_entry(conn, ledger_id: int, entry_date: str, transaction_type: str,
                        transaction_number: str, particulars: str, description: str,
                        item_name: str, qty_15_yards: float, qty_22_yards: float,
                        total_qty_debit: float, total_qty_credit: float):
    """Create a ledger entry and calculate balance"""
    cursor = conn.cursor()
    try:
        # Get last balance
        last_balance = get_last_balance(conn, ledger_id)
        
        # Calculate new balance (Debit increases, Credit decreases)
        new_balance = last_balance + total_qty_debit - total_qty_credit
        
        # Insert entry
        cursor.execute("""
            INSERT INTO stock_ledger_entries
            (ledger_id, entry_date, transaction_type, transaction_number,
             particulars, description, item_name, qty_15_yards, qty_22_yards,
             total_qty_debit, total_qty_credit, balance)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (ledger_id, entry_date, transaction_type, transaction_number,
              particulars, description, item_name, qty_15_yards, qty_22_yards,
              total_qty_debit, total_qty_credit, new_balance))
    finally:
        cursor.close()


def delete_ledger_entries_by_transaction(conn, transaction_number: str):
    """Delete all ledger entries for a specific transaction number and recalculate balances"""
    cursor = conn.cursor()
    try:
        # Get all entries for this transaction
        cursor.execute("""
            SELECT ledger_id, total_qty_debit, total_qty_credit, entry_date, id
            FROM stock_ledger_entries
            WHERE transaction_number = %s
            ORDER BY entry_date ASC, id ASC
        """, (transaction_number,))
        entries_to_delete = cursor.fetchall()
        
        if not entries_to_delete:
            return
        
        # Group by ledger_id to recalculate balances
        ledger_entries = {}
        for entry in entries_to_delete:
            ledger_id = entry[0]
            if ledger_id not in ledger_entries:
                ledger_entries[ledger_id] = []
            ledger_entries[ledger_id].append(entry)
        
        # Delete entries
        cursor.execute("""
            DELETE FROM stock_ledger_entries
            WHERE transaction_number = %s
        """, (transaction_number,))
        
        # Recalculate balances for affected ledgers
        for ledger_id in ledger_entries.keys():
            _recalculate_ledger_balance(conn, ledger_id)
    finally:
        cursor.close()


def _recalculate_ledger_balance(conn, ledger_id: int):
    """Recalculate all balances for a ledger after entry deletion/update"""
    cursor = conn.cursor()
    try:
        # Get all entries for this ledger in chronological order
        cursor.execute("""
            SELECT id, total_qty_debit, total_qty_credit
            FROM stock_ledger_entries
            WHERE ledger_id = %s
            ORDER BY entry_date ASC, id ASC
        """, (ledger_id,))
        entries = cursor.fetchall()
        
        # Recalculate running balance
        running_balance = 0.0
        for entry in entries:
            entry_id, debit, credit = entry
            running_balance = running_balance + float(debit) - float(credit)
            
            # Update balance for this entry
            cursor.execute("""
                UPDATE stock_ledger_entries
                SET balance = %s
                WHERE id = %s
            """, (running_balance, entry_id))
    finally:
        cursor.close()

