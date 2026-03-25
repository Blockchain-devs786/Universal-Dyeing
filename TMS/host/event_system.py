"""Event System for Delta-Only WebSocket Broadcasting

In-memory event log with monotonic IDs (resets on server restart).
"""

from typing import Dict, List, Optional
from datetime import datetime
import threading
from collections import deque

# Protocol version for events (required for clients)
EVENT_VERSION = 1

# In-memory event log (max 10000 events to prevent memory bloat)
MAX_EVENTS = 10000
event_log: deque = deque(maxlen=MAX_EVENTS)
event_counter = 0
event_lock = threading.Lock()


def get_next_event_id() -> int:
    """Get next sequential event ID"""
    global event_counter
    with event_lock:
        event_counter += 1
        return event_counter


def _ensure_version(payload: Dict) -> Dict:
    """Ensure version is attached to payload"""
    if "version" not in payload:
        payload["version"] = EVENT_VERSION
    return payload


def log_event(event_type: str, entity_type: str, entity_id: int, delta_data: Dict) -> int:
    """Log an event and return event ID"""
    delta_with_version = _ensure_version(delta_data.copy())
    event_id = get_next_event_id()
    event = {
        "event_id": event_id,
        "event": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "data": delta_with_version,
        "timestamp": datetime.now().isoformat(),
        "version": EVENT_VERSION,
    }
    with event_lock:
        event_log.append(event)
    return event_id


def get_events_since(event_id: int) -> List[Dict]:
    """Get all events since the given event_id"""
    with event_lock:
        return [event for event in event_log if event["event_id"] > event_id]


def get_last_event_id() -> int:
    """Get the last event ID (0 if no events)"""
    with event_lock:
        return event_counter if event_log else 0


# Event type constants
EVENT_INWARD_CREATED = "INWARD_CREATED"
EVENT_INWARD_UPDATED = "INWARD_UPDATED"
EVENT_INWARD_DELETED = "INWARD_DELETED"
EVENT_TRANSFER_CREATED = "TRANSFER_CREATED"
EVENT_TRANSFER_UPDATED = "TRANSFER_UPDATED"
EVENT_TRANSFER_DELETED = "TRANSFER_DELETED"
EVENT_OUTWARD_CREATED = "OUTWARD_CREATED"
EVENT_OUTWARD_UPDATED = "OUTWARD_UPDATED"
EVENT_OUTWARD_DELETED = "OUTWARD_DELETED"
EVENT_INVOICE_CREATED = "INVOICE_CREATED"
EVENT_INVOICE_UPDATED = "INVOICE_UPDATED"
EVENT_INVOICE_DELETED = "INVOICE_DELETED"
EVENT_STOCK_DELTA_UPDATED = "STOCK_DELTA_UPDATED"
EVENT_TRANSFER_CREATED = "TRANSFER_CREATED"
EVENT_TRANSFER_UPDATED = "TRANSFER_UPDATED"
EVENT_TRANSFER_DELETED = "TRANSFER_DELETED"


def create_inward_delta_event(document_id: int, ms_party_id: int, total_quantity: float, 
                              inward_number: str, document_date: str) -> Dict:
    """Create a minimal delta event for inward creation"""
    return {
        "version": EVENT_VERSION,
        "event": EVENT_INWARD_CREATED,
        "id": document_id,
        "ms_party_id": ms_party_id,
        "total_quantity": total_quantity,
        "inward_number": inward_number,
        "document_date": document_date
    }


def create_stock_delta_event(party_id: int, item_name: str, measurement: int, delta: float) -> Dict:
    """Create a minimal delta event for stock update"""
    return {
        "version": EVENT_VERSION,
        "event": EVENT_STOCK_DELTA_UPDATED,
        "party_id": party_id,
        "item_name": item_name,
        "measurement": measurement,
        "delta": delta
    }


def create_transfer_delta_event(document_id: int, ms_party_id: int, total_quantity: float,
                                transfer_number: str, transfer_type: str, document_date: str) -> Dict:
    """Create a minimal delta event for transfer creation"""
    return {
        "version": EVENT_VERSION,
        "event": EVENT_TRANSFER_CREATED,
        "id": document_id,
        "ms_party_id": ms_party_id,
        "total_quantity": total_quantity,
        "transfer_number": transfer_number,
        "transfer_type": transfer_type,
        "document_date": document_date
    }

