"""Financial Ledger Manager"""

import mysql.connector
from datetime import datetime
from typing import Optional, Dict, List
from host.db_pool import db_pool

def get_or_create_financial_ledger(cursor, name: str, party_id: Optional[int] = None, is_default: bool = False) -> int:
    """Get or create a financial ledger by name or party_id"""
    if party_id:
        cursor.execute("SELECT id FROM financial_ledgers WHERE party_id = %s", (party_id,))
    else:
        cursor.execute("SELECT id FROM financial_ledgers WHERE name = %s", (name,))
    
    row = cursor.fetchone()
    if row:
        # Handle both dictionary and tuple cursors
        if isinstance(row, dict):
            return row['id']
        return row[0]
    
    # Create new ledger
    cursor.execute("""
        INSERT INTO financial_ledgers (name, party_id, is_default)
        VALUES (%s, %s, %s)
    """, (name, party_id, is_default))
    return cursor.lastrowid

def post_invoice_to_ledgers(invoice_id: int, conn) -> bool:
    """
    Post invoice entries to financial ledgers:
    1. Debit Party Ledger (Asset increases)
    2. Credit 'Dyeing service charges' Ledger (Income increases)
    """
    cursor = conn.cursor(dictionary=True)
    try:
        # Get invoice details
        cursor.execute("""
            SELECT i.invoice_number, i.ms_party_id, i.total_amount, i.invoice_date,
                   l.name as party_name
            FROM invoices i
            JOIN liabilities l ON i.ms_party_id = l.id
            WHERE i.id = %s
        """, (invoice_id,))
        invoice = cursor.fetchone()
        
        if not invoice:
            return False
        
        # 1. Get ledgers
        party_ledger_id = get_or_create_financial_ledger(cursor, invoice['party_name'], party_id=invoice['ms_party_id'])
        income_ledger_id = get_or_create_financial_ledger(cursor, 'Dyeing service charges', is_default=True)
        
        # 2. Post to Party Ledger (Debit)
        # Particular: 'Dyeing services', Description: 'Dyeing charges'
        cursor.execute("""
            INSERT INTO financial_ledger_entries 
            (ledger_id, entry_date, particulars, invoice_number, description, debit, credit, balance)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            party_ledger_id, invoice['invoice_date'], 'Dyeing services', 
            invoice['invoice_number'], 'Dyeing charges', invoice['total_amount'], 0.00, 0.00
        ))
        
        # 3. Post to Income Ledger (Credit)
        # Particular: Party Name, Description: 'service income'
        cursor.execute("""
            INSERT INTO financial_ledger_entries 
            (ledger_id, entry_date, particulars, invoice_number, description, debit, credit, balance)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            income_ledger_id, invoice['invoice_date'], invoice['party_name'], 
            invoice['invoice_number'], 'service income', 0.00, invoice['total_amount'], 0.00
        ))
        
        # 4. Update balances for both ledgers
        update_ledger_balances(cursor, party_ledger_id)
        update_ledger_balances(cursor, income_ledger_id)
        
        return True
    except Exception as e:
        print(f"Error posting invoice to ledgers: {e}")
        return False
    finally:
        cursor.close()

def reverse_invoice_from_ledgers(invoice_number: str, conn) -> bool:
    """Remove all ledger entries associated with an invoice number"""
    cursor = conn.cursor()
    try:
        # Get ledger IDs before deleting entries to update their balances later
        cursor.execute("""
            SELECT DISTINCT ledger_id FROM financial_ledger_entries 
            WHERE invoice_number = %s
        """, (invoice_number,))
        ledger_ids = [row[0] for row in cursor.fetchall()]
        
        # Delete entries
        cursor.execute("DELETE FROM financial_ledger_entries WHERE invoice_number = %s", (invoice_number,))
        
        # Update balances
        for ledger_id in ledger_ids:
            update_ledger_balances(cursor, ledger_id)
            
        return True
    except Exception as e:
        print(f"Error reversing invoice from ledgers: {e}")
        return False
    finally:
        cursor.close()

def update_ledger_balances(cursor, ledger_id: int):
    """Recalculate running balance for a ledger"""
    # Use a non-dictionary cursor if needed, or handle dictionary results
    cursor.execute("""
        SELECT id, debit, credit FROM financial_ledger_entries 
        WHERE ledger_id = %s 
        ORDER BY entry_date ASC, id ASC
    """, (ledger_id,))
    entries = cursor.fetchall()
    
    running_balance = 0.00
    for entry in entries:
        # Handle both dictionary and tuple cursors
        if isinstance(entry, dict):
            entry_id = entry['id']
            debit = entry['debit']
            credit = entry['credit']
        else:
            entry_id, debit, credit = entry
            
        running_balance += float(debit or 0) - float(credit or 0)
        
        cursor.execute("""
            UPDATE financial_ledger_entries SET balance = %s WHERE id = %s
        """, (running_balance, entry_id))
