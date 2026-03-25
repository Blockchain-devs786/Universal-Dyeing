"""Utility functions for generating edit log history descriptions"""

from typing import Dict, List, Optional, Any


def generate_edit_log(old_data: Dict, new_data: Dict, old_items: List[Dict] = None, new_items: List[Dict] = None, 
                     field_labels: Dict[str, str] = None) -> str:
    """
    Generate a human-readable edit log description comparing old and new data.
    
    Args:
        old_data: Dictionary of old field values
        new_data: Dictionary of new field values
        old_items: List of old items (for forms with item lists)
        new_items: List of new items (for forms with item lists)
        field_labels: Optional mapping of field names to display labels
    
    Returns:
        String description of all changes
    """
    changes = []
    
    # Default field labels
    if field_labels is None:
        field_labels = {}
    
    def get_label(field_name: str) -> str:
        return field_labels.get(field_name, field_name.replace('_', ' ').title())
    
    # Compare main fields
    all_fields = set(old_data.keys()) | set(new_data.keys())
    for field in all_fields:
        old_val = old_data.get(field)
        new_val = new_data.get(field)
        
        # Skip internal fields
        if field in ['id', 'created_by', 'created_at', 'edited_by', 'edit_log_history']:
            continue
        
        # Handle None values
        old_val_str = str(old_val) if old_val is not None else ''
        new_val_str = str(new_val) if new_val is not None else ''
        
        # Compare values
        if old_val_str != new_val_str:
            label = get_label(field)
            changes.append(f"{label} changed from '{old_val_str}' to '{new_val_str}'")
    
    # Compare items if provided
    if old_items is not None and new_items is not None:
        item_changes = compare_items(old_items, new_items)
        if item_changes:
            changes.extend(item_changes)
    
    if not changes:
        return "No changes detected"
    
    return "; ".join(changes)


def compare_items(old_items: List[Dict], new_items: List[Dict]) -> List[str]:
    """
    Compare old and new item lists and generate change descriptions.
    
    Returns:
        List of change descriptions
    """
    changes = []
    
    # Create lookup dictionaries for items
    old_items_dict = {}
    for item in old_items:
        key = (item.get('item_name', ''), item.get('measurement', ''))
        old_items_dict[key] = item
    
    new_items_dict = {}
    for item in new_items:
        key = (item.get('item_name', ''), item.get('measurement', ''))
        new_items_dict[key] = item
    
    # Find removed items
    removed_keys = set(old_items_dict.keys()) - set(new_items_dict.keys())
    for key in removed_keys:
        item = old_items_dict[key]
        item_name = item.get('item_name', '')
        measurement = item.get('measurement', '')
        quantity = item.get('quantity', 0)
        changes.append(f"Removed item: {item_name} ({measurement}) - Quantity: {quantity}")
    
    # Find added items
    added_keys = set(new_items_dict.keys()) - set(old_items_dict.keys())
    for key in added_keys:
        item = new_items_dict[key]
        item_name = item.get('item_name', '')
        measurement = item.get('measurement', '')
        quantity = item.get('quantity', 0)
        changes.append(f"Added item: {item_name} ({measurement}) - Quantity: {quantity}")
    
    # Find modified items (same item but different quantity)
    common_keys = set(old_items_dict.keys()) & set(new_items_dict.keys())
    for key in common_keys:
        old_item = old_items_dict[key]
        new_item = new_items_dict[key]
        old_qty = old_item.get('quantity', 0)
        new_qty = new_item.get('quantity', 0)
        
        if old_qty != new_qty:
            item_name = old_item.get('item_name', '')
            measurement = old_item.get('measurement', '')
            changes.append(f"Item {item_name} ({measurement}) quantity changed from {old_qty} to {new_qty}")
    
    return changes


def generate_inward_edit_log(old_doc: Dict, new_doc: Dict, old_items: List[Dict], new_items: List[Dict], 
                             party_names: Dict[int, str] = None) -> str:
    """Generate edit log specifically for inward documents"""
    field_labels = {
        'ms_party_id': 'MS Party',
        'from_party': 'From Party',
        'vehicle_number': 'Vehicle Number',
        'driver_name': 'Driver Name',
        'document_date': 'Document Date',
        'total_quantity': 'Total Quantity'
    }
    
    # Convert party IDs to names if provided
    old_data = old_doc.copy()
    new_data = new_doc.copy()
    
    if party_names:
        if old_data.get('ms_party_id'):
            old_data['ms_party_id'] = party_names.get(old_data['ms_party_id'], f"Party ID {old_data['ms_party_id']}")
        if new_data.get('ms_party_id'):
            new_data['ms_party_id'] = party_names.get(new_data['ms_party_id'], f"Party ID {new_data['ms_party_id']}")
    
    return generate_edit_log(old_data, new_data, old_items, new_items, field_labels)


def generate_transfer_edit_log(old_doc: Dict, new_doc: Dict, old_items: List[Dict], new_items: List[Dict],
                               party_names: Dict[int, str] = None) -> str:
    """Generate edit log specifically for transfer documents"""
    field_labels = {
        'ms_party_id': 'MS Party',
        'from_party': 'From Party',
        'transfer_to': 'Transfer To',
        'vehicle_number': 'Vehicle Number',
        'driver_name': 'Driver Name',
        'document_date': 'Document Date',
        'total_quantity': 'Total Quantity'
    }
    
    old_data = old_doc.copy()
    new_data = new_doc.copy()
    
    if party_names:
        if old_data.get('ms_party_id'):
            old_data['ms_party_id'] = party_names.get(old_data['ms_party_id'], f"Party ID {old_data['ms_party_id']}")
        if new_data.get('ms_party_id'):
            new_data['ms_party_id'] = party_names.get(new_data['ms_party_id'], f"Party ID {new_data['ms_party_id']}")
    
    return generate_edit_log(old_data, new_data, old_items, new_items, field_labels)


def generate_outward_edit_log(old_doc: Dict, new_doc: Dict, old_items: List[Dict], new_items: List[Dict],
                              party_names: Dict[int, str] = None) -> str:
    """Generate edit log specifically for outward documents"""
    field_labels = {
        'ms_party_id': 'MS Party',
        'from_party': 'From Party',
        'outward_to': 'Outward To',
        'vehicle_number': 'Vehicle Number',
        'driver_name': 'Driver Name',
        'document_date': 'Document Date',
        'total_quantity': 'Total Quantity'
    }
    
    old_data = old_doc.copy()
    new_data = new_doc.copy()
    
    if party_names:
        if old_data.get('ms_party_id'):
            old_data['ms_party_id'] = party_names.get(old_data['ms_party_id'], f"Party ID {old_data['ms_party_id']}")
        if new_data.get('ms_party_id'):
            new_data['ms_party_id'] = party_names.get(new_data['ms_party_id'], f"Party ID {new_data['ms_party_id']}")
    
    return generate_edit_log(old_data, new_data, old_items, new_items, field_labels)


def generate_invoice_edit_log(old_doc: Dict, new_doc: Dict, old_items: List[Dict], new_items: List[Dict],
                              party_names: Dict[int, str] = None, 
                              old_outward_ids: set = None, new_outward_ids: set = None,
                              old_outward_numbers: Dict[int, str] = None, new_outward_numbers: Dict[int, str] = None) -> str:
    """Generate edit log specifically for invoice documents"""
    field_labels = {
        'ms_party_id': 'MS Party',
        'discount_amount': 'Discount Amount',
        'discount_source': 'Discount Source',
        'invoice_date': 'Invoice Date',
        'total_amount': 'Total Amount',
        'number_of_items': 'Number of Items'
    }
    
    old_data = old_doc.copy()
    new_data = new_doc.copy()
    
    if party_names:
        if old_data.get('ms_party_id'):
            old_data['ms_party_id'] = party_names.get(old_data['ms_party_id'], f"Party ID {old_data['ms_party_id']}")
        if new_data.get('ms_party_id'):
            new_data['ms_party_id'] = party_names.get(new_data['ms_party_id'], f"Party ID {new_data['ms_party_id']}")
    
    # Generate base edit log
    changes = []
    
    # Compare main fields
    all_fields = set(old_data.keys()) | set(new_data.keys())
    for field in all_fields:
        old_val = old_data.get(field)
        new_val = new_data.get(field)
        
        # Skip internal fields
        if field in ['id', 'created_by', 'created_at', 'edited_by', 'edit_log_history', 'invoice_number']:
            continue
        
        # Handle None values
        old_val_str = str(old_val) if old_val is not None else ''
        new_val_str = str(new_val) if new_val is not None else ''
        
        # Compare values
        if old_val_str != new_val_str:
            label = field_labels.get(field, field.replace('_', ' ').title())
            changes.append(f"{label} changed from '{old_val_str}' to '{new_val_str}'")
    
    # Track outward document changes (use numbers if available, otherwise IDs)
    if old_outward_ids is not None and new_outward_ids is not None:
        removed_outwards = old_outward_ids - new_outward_ids
        added_outwards = new_outward_ids - old_outward_ids
        
        if removed_outwards:
            # Use outward numbers if available, otherwise use IDs
            if old_outward_numbers:
                outward_list = ','.join(sorted([old_outward_numbers.get(oid, str(oid)) for oid in removed_outwards]))
            else:
                outward_list = ','.join(sorted([str(oid) for oid in removed_outwards]))
            changes.append(f"Removed outward {outward_list}")
        
        if added_outwards:
            # Use outward numbers if available, otherwise use IDs
            if new_outward_numbers:
                outward_list = ','.join(sorted([new_outward_numbers.get(oid, str(oid)) for oid in added_outwards]))
            else:
                outward_list = ','.join(sorted([str(oid) for oid in added_outwards]))
            changes.append(f"Added outward {outward_list}")
    
    # Compare items if provided
    if old_items is not None and new_items is not None:
        item_changes = compare_items(old_items, new_items)
        if item_changes:
            changes.extend(item_changes)
    
    if not changes:
        return "No changes detected"
    
    return "; ".join(changes)


def generate_voucher_edit_log(old_doc: Dict, new_doc: Dict, old_details: List[Dict], new_details: List[Dict],
                              party_names: Dict[int, str] = None, asset_names: Dict[int, str] = None,
                              expense_names: Dict[int, str] = None, vendor_names: Dict[int, str] = None) -> str:
    """Generate edit log specifically for voucher documents (CP, CR, JV)"""
    field_labels = {
        'voucher_type': 'Voucher Type',
        'voucher_date': 'Voucher Date',
        'description': 'Description',
        'total_amount': 'Total Amount'
    }
    
    old_data = old_doc.copy()
    new_data = new_doc.copy()
    
    # Generate base edit log
    changes = []
    
    # Compare main fields
    all_fields = set(old_data.keys()) | set(new_data.keys())
    for field in all_fields:
        old_val = old_data.get(field)
        new_val = new_data.get(field)
        
        # Skip internal fields
        if field in ['id', 'voucher_no', 'created_by', 'created_at', 'updated_at', 'edited_by', 'edit_log_history']:
            continue
        
        # Handle None values
        old_val_str = str(old_val) if old_val is not None else ''
        new_val_str = str(new_val) if new_val is not None else ''
        
        # Compare values
        if old_val_str != new_val_str:
            label = field_labels.get(field, field.replace('_', ' ').title())
            changes.append(f"{label} changed from '{old_val_str}' to '{new_val_str}'")
    
    # Compare voucher details
    if old_details is not None and new_details is not None:
        detail_changes = compare_voucher_details(old_details, new_details, party_names, asset_names, expense_names, vendor_names)
        if detail_changes:
            changes.extend(detail_changes)
    
    if not changes:
        return "No changes detected"
    
    return "; ".join(changes)


def compare_voucher_details(old_details: List[Dict], new_details: List[Dict],
                           party_names: Dict[int, str] = None, asset_names: Dict[int, str] = None,
                           expense_names: Dict[int, str] = None, vendor_names: Dict[int, str] = None) -> List[str]:
    """
    Compare old and new voucher detail lists and generate change descriptions.
    
    Returns:
        List of change descriptions
    """
    changes = []
    
    # Helper function to get account name
    def get_account_name(detail):
        if detail.get('party_id'):
            return party_names.get(detail['party_id'], f"Party ID {detail['party_id']}") if party_names else f"Party ID {detail['party_id']}"
        elif detail.get('asset_id'):
            return asset_names.get(detail['asset_id'], f"Asset ID {detail['asset_id']}") if asset_names else f"Asset ID {detail['asset_id']}"
        elif detail.get('expense_id'):
            return expense_names.get(detail['expense_id'], f"Expense ID {detail['expense_id']}") if expense_names else f"Expense ID {detail['expense_id']}"
        elif detail.get('vendor_id'):
            return vendor_names.get(detail['vendor_id'], f"Vendor ID {detail['vendor_id']}") if vendor_names else f"Vendor ID {detail['vendor_id']}"
        return "Unknown Account"
    
    # Create lookup dictionaries for details using account info and amounts
    old_details_dict = {}
    for detail in old_details:
        account_name = get_account_name(detail)
        debit = detail.get('debit_amount', 0) or 0
        credit = detail.get('credit_amount', 0) or 0
        key = (account_name, debit, credit)
        old_details_dict[key] = detail
    
    new_details_dict = {}
    for detail in new_details:
        account_name = get_account_name(detail)
        debit = detail.get('debit_amount', 0) or 0
        credit = detail.get('credit_amount', 0) or 0
        key = (account_name, debit, credit)
        new_details_dict[key] = detail
    
    # Find removed details
    removed_keys = set(old_details_dict.keys()) - set(new_details_dict.keys())
    for key in removed_keys:
        detail = old_details_dict[key]
        account_name = key[0]
        debit = key[1]
        credit = key[2]
        if debit > 0:
            changes.append(f"Removed debit entry: {account_name} - Amount: {debit}")
        elif credit > 0:
            changes.append(f"Removed credit entry: {account_name} - Amount: {credit}")
    
    # Find added details
    added_keys = set(new_details_dict.keys()) - set(old_details_dict.keys())
    for key in added_keys:
        detail = new_details_dict[key]
        account_name = key[0]
        debit = key[1]
        credit = key[2]
        if debit > 0:
            changes.append(f"Added debit entry: {account_name} - Amount: {debit}")
        elif credit > 0:
            changes.append(f"Added credit entry: {account_name} - Amount: {credit}")
    
    return changes
