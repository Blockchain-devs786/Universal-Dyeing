"""Voucher Manager - Handles voucher posting to financial ledgers"""

import mysql.connector
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from host.db_pool import db_pool
from host.ledger_manager import get_or_create_financial_ledger, update_ledger_balances


def get_next_voucher_number(voucher_type: str, conn) -> str:
    """Generate next voucher number based on type"""
    cursor = conn.cursor()
    try:
        # Get current year
        current_year = datetime.now().year
        
        # Find the highest voucher number for this type and year
        pattern = f"{voucher_type}-{current_year}-%"
        cursor.execute("""
            SELECT voucher_no FROM voucher_master 
            WHERE voucher_no LIKE %s 
            ORDER BY voucher_no DESC LIMIT 1
        """, (pattern,))
        result = cursor.fetchone()
        
        if result:
            # Extract number and increment
            last_no = result[0]
            parts = last_no.split('-')
            if len(parts) == 3:
                try:
                    num = int(parts[2])
                    next_num = num + 1
                except ValueError:
                    next_num = 1
            else:
                next_num = 1
        else:
            next_num = 1
        
        return f"{voucher_type}-{current_year}-{next_num:04d}"
    finally:
        cursor.close()


def post_voucher_to_ledgers(voucher_id: int, conn) -> bool:
    """
    Post voucher entries to financial ledgers based on voucher type.
    Handles CP, CR, and JV with special particulars logic for JV.
    """
    cursor = conn.cursor(dictionary=True)
    try:
        # Get voucher master details
        cursor.execute("""
            SELECT id, voucher_no, voucher_type, voucher_date, description, total_amount
            FROM voucher_master
            WHERE id = %s
        """, (voucher_id,))
        voucher = cursor.fetchone()
        
        if not voucher:
            return False
        
        # Get voucher details
        cursor.execute("""
            SELECT vd.id, vd.party_id, vd.asset_id, vd.expense_id, vd.vendor_id,
                   vd.debit_amount, vd.credit_amount,
                   COALESCE(l.name, a.name, e.name, v.name, '') as party_name,
                   CASE 
                       WHEN vd.party_id IS NOT NULL THEN 'liability'
                       WHEN vd.asset_id IS NOT NULL THEN 'asset'
                       WHEN vd.expense_id IS NOT NULL THEN 'expense'
                       WHEN vd.vendor_id IS NOT NULL THEN 'vendor'
                       ELSE 'unknown'
                   END as party_type
            FROM voucher_detail vd
            LEFT JOIN liabilities l ON vd.party_id = l.id
            LEFT JOIN assets a ON vd.asset_id = a.id
            LEFT JOIN expenses e ON vd.expense_id = e.id
            LEFT JOIN vendors v ON vd.vendor_id = v.id
            WHERE vd.voucher_id = %s
        """, (voucher_id,))
        details = cursor.fetchall()
        
        if not details:
            return False
        
        voucher_type = voucher['voucher_type']
        voucher_no = voucher['voucher_no']
        voucher_date = voucher['voucher_date']
        description = voucher['description'] or ''
        
        if voucher_type == 'CP':
            # Cash Payment: FROM Assets (Cash) -> Credit, TO Liabilities/Expenses/Vendors -> Debit
            # Only one cash account allowed
            cash_account = None
            to_account = None
            
            for detail in details:
                if detail.get('asset_id'):
                    cash_account = detail
                elif detail.get('party_id') or detail.get('expense_id') or detail.get('vendor_id'):
                    to_account = detail
            
            if not cash_account or not to_account:
                return False
            
            # Get or create ledgers
            from_ledger_id = get_or_create_financial_ledger(
                cursor, cash_account['party_name'], party_id=None, is_default=False
            )
            
            # For TO account, check if it's a party, expense, or vendor
            if to_account.get('party_id'):
                to_ledger_id = get_or_create_financial_ledger(
                    cursor, to_account['party_name'], party_id=to_account['party_id']
                )
            elif to_account.get('expense_id') or to_account.get('vendor_id'):
                # Expense or vendor - no party_id, use name-based lookup
                to_ledger_id = get_or_create_financial_ledger(
                    cursor, to_account['party_name'], party_id=None, is_default=False
                )
            else:
                # Fallback
                to_ledger_id = get_or_create_financial_ledger(
                    cursor, to_account['party_name'], party_id=None, is_default=False
                )
            
            if not from_ledger_id or not to_ledger_id:
                print(f"Error: Failed to get ledger IDs. From: {from_ledger_id}, To: {to_ledger_id}")
                return False
            
            amount = cash_account['debit_amount'] or cash_account['credit_amount'] or 0
            
            # Post to TO Account (Debit) - TO party receives debit
            cursor.execute("""
                INSERT INTO financial_ledger_entries 
                (ledger_id, entry_date, particulars, voucher_number, description, debit, credit, balance)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                to_ledger_id, voucher_date, cash_account['party_name'],
                voucher_no, description, amount, 0.00, 0.00
            ))
            
            # Post to FROM Account (Credit) - FROM party (cash) receives credit
            cursor.execute("""
                INSERT INTO financial_ledger_entries 
                (ledger_id, entry_date, particulars, voucher_number, description, debit, credit, balance)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                from_ledger_id, voucher_date, to_account['party_name'],
                voucher_no, description, 0.00, amount, 0.00
            ))
            
            # Update balances
            update_ledger_balances(cursor, to_ledger_id)
            update_ledger_balances(cursor, from_ledger_id)
            
        elif voucher_type == 'CR':
            # Cash Receipt: From Party -> Credit, To Party -> Debit
            # UI sends: FROM has debit_amount, TO has credit_amount
            # But we need: TO ledger -> Debit, FROM ledger -> Credit
            from_account = None
            to_account = None
            
            for detail in details:
                if detail['debit_amount']:
                    # Debit entry in UI = FROM party (will post as Credit)
                    from_account = detail
                elif detail['credit_amount']:
                    # Credit entry in UI = TO party (will post as Debit)
                    to_account = detail
            
            if not from_account or not to_account:
                return False
            
            # Get or create ledgers
            from_ledger_id = None
            to_ledger_id = None
            
            # FROM account can be liability, expense, or vendor
            if from_account.get('party_id'):
                from_ledger_id = get_or_create_financial_ledger(
                    cursor, from_account['party_name'], party_id=from_account['party_id']
                )
            elif from_account.get('expense_id') or from_account.get('vendor_id'):
                # Expense or vendor - use name-based lookup
                from_ledger_id = get_or_create_financial_ledger(
                    cursor, from_account['party_name'], party_id=None, is_default=False
                )
            elif from_account.get('asset_id'):
                from_ledger_id = get_or_create_financial_ledger(
                    cursor, from_account['party_name'], party_id=None, is_default=False
                )
            
            # TO account should be asset (cash)
            if to_account.get('asset_id'):
                to_ledger_id = get_or_create_financial_ledger(
                    cursor, to_account['party_name'], party_id=None, is_default=False
                )
            elif to_account.get('party_id'):
                to_ledger_id = get_or_create_financial_ledger(
                    cursor, to_account['party_name'], party_id=to_account['party_id']
                )
            
            if not from_ledger_id or not to_ledger_id:
                print(f"Error: Failed to get ledger IDs. From: {from_ledger_id}, To: {to_ledger_id}")
                print(f"From account: {from_account}")
                print(f"To account: {to_account}")
                return False
            
            amount = to_account['credit_amount'] or from_account['debit_amount'] or 0
            
            # Post to TO Account (Debit) - TO party receives debit
            cursor.execute("""
                INSERT INTO financial_ledger_entries 
                (ledger_id, entry_date, particulars, voucher_number, description, debit, credit, balance)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                to_ledger_id, voucher_date, from_account['party_name'],
                voucher_no, description, amount, 0.00, 0.00
            ))
            
            # Post to FROM Account (Credit) - FROM party receives credit
            cursor.execute("""
                INSERT INTO financial_ledger_entries 
                (ledger_id, entry_date, particulars, voucher_number, description, debit, credit, balance)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                from_ledger_id, voucher_date, to_account['party_name'],
                voucher_no, description, 0.00, amount, 0.00
            ))
            
            # Update balances
            update_ledger_balances(cursor, to_ledger_id)
            update_ledger_balances(cursor, from_ledger_id)
            
        elif voucher_type == 'JV':
            # Journal Voucher: Special particulars logic
            # For debit entries: particulars = all credit-side parties
            # For credit entries: particulars = all debit-side parties
            
            # Separate debit and credit entries
            debit_entries = [d for d in details if d['debit_amount']]
            credit_entries = [d for d in details if d['credit_amount']]
            
            # Collect party names for particulars
            credit_party_names = [e['party_name'] for e in credit_entries]
            debit_party_names = [e['party_name'] for e in debit_entries]
            
            credit_particulars = ', '.join(credit_party_names) if credit_party_names else ''
            debit_particulars = ', '.join(debit_party_names) if debit_party_names else ''
            
            # Post debit entries
            for entry in debit_entries:
                ledger_id = None
                if entry.get('party_id'):
                    ledger_id = get_or_create_financial_ledger(
                        cursor, entry['party_name'], party_id=entry['party_id']
                    )
                elif entry.get('asset_id'):
                    ledger_id = get_or_create_financial_ledger(
                        cursor, entry['party_name'], party_id=None, is_default=False
                    )
                elif entry.get('expense_id') or entry.get('vendor_id'):
                    ledger_id = get_or_create_financial_ledger(
                        cursor, entry['party_name'], party_id=None, is_default=False
                    )
                
                if ledger_id:
                    cursor.execute("""
                        INSERT INTO financial_ledger_entries 
                        (ledger_id, entry_date, particulars, voucher_number, description, debit, credit, balance)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        ledger_id, voucher_date, credit_particulars,
                        voucher_no, description, entry['debit_amount'], 0.00, 0.00
                    ))
            
            # Post credit entries
            for entry in credit_entries:
                ledger_id = None
                if entry.get('party_id'):
                    ledger_id = get_or_create_financial_ledger(
                        cursor, entry['party_name'], party_id=entry['party_id']
                    )
                elif entry.get('asset_id'):
                    ledger_id = get_or_create_financial_ledger(
                        cursor, entry['party_name'], party_id=None, is_default=False
                    )
                elif entry.get('expense_id') or entry.get('vendor_id'):
                    ledger_id = get_or_create_financial_ledger(
                        cursor, entry['party_name'], party_id=None, is_default=False
                    )
                
                if ledger_id:
                    cursor.execute("""
                        INSERT INTO financial_ledger_entries 
                        (ledger_id, entry_date, particulars, voucher_number, description, debit, credit, balance)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        ledger_id, voucher_date, debit_particulars,
                        voucher_no, description, 0.00, entry['credit_amount'], 0.00
                    ))
            
            # Update balances for all affected ledgers
            all_ledger_ids = set()
            # Collect ledger IDs from posted entries
            for entry in debit_entries + credit_entries:
                if entry.get('party_id'):
                    ledger_id = get_or_create_financial_ledger(
                        cursor, entry['party_name'], party_id=entry['party_id']
                    )
                    all_ledger_ids.add(ledger_id)
                elif entry.get('asset_id'):
                    ledger_id = get_or_create_financial_ledger(
                        cursor, entry['party_name'], party_id=None, is_default=False
                    )
                    all_ledger_ids.add(ledger_id)
                elif entry.get('expense_id') or entry.get('vendor_id'):
                    ledger_id = get_or_create_financial_ledger(
                        cursor, entry['party_name'], party_id=None, is_default=False
                    )
                    all_ledger_ids.add(ledger_id)
            
            for ledger_id in all_ledger_ids:
                update_ledger_balances(cursor, ledger_id)
        
        return True
    except Exception as e:
        print(f"Error posting voucher to ledgers: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cursor.close()


def reverse_voucher_from_ledgers(voucher_no: str, conn) -> bool:
    """Remove all ledger entries associated with a voucher number"""
    cursor = conn.cursor()
    try:
        # Get ledger IDs before deleting entries to update their balances later
        cursor.execute("""
            SELECT DISTINCT ledger_id FROM financial_ledger_entries 
            WHERE voucher_number = %s
        """, (voucher_no,))
        ledger_ids = [row[0] for row in cursor.fetchall()]
        
        # Delete entries
        cursor.execute("DELETE FROM financial_ledger_entries WHERE voucher_number = %s", (voucher_no,))
        
        # Update balances
        for ledger_id in ledger_ids:
            update_ledger_balances(cursor, ledger_id)
            
        return True
    except Exception as e:
        print(f"Error reversing voucher from ledgers: {e}")
        return False
    finally:
        cursor.close()
