"""Snapshot and Sync APIs for Read-Optimized Client Caching

- GET /api/snapshot/bootstrap - One-time cache load on login
- GET /api/sync/events - Incremental event sync
- GET /api/stock/snapshot/{party_id} - Stock snapshot (replaces repeated GET /api/stock/{party_id})
"""

from fastapi import HTTPException, Request, Query
from typing import Dict, List, Optional
from host.db_pool import db_pool
from host.api_server import app, rate_limit_check, get_client_ip
from host.event_system import get_events_since, get_last_event_id


@app.get("/api/snapshot/bootstrap")
async def get_bootstrap_snapshot(request: Request):
    """
    Get initial snapshot for client cache (call once on login).
    
    Returns:
    {
        "parties": [...],
        "stock": [...],  # All stock records
        "last_event_id": 12345
    }
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
        
        # Get all parties (minimal fields for cache)
        cursor.execute("""
            SELECT id, name, rate_15_yards, rate_22_yards, discount_percent
            FROM liabilities
            ORDER BY name
        """)
        parties = cursor.fetchall()
        for party in parties:
            party['rate_15_yards'] = float(party.get('rate_15_yards', 0))
            party['rate_22_yards'] = float(party.get('rate_22_yards', 0))
            party['discount_percent'] = float(party.get('discount_percent', 0))
        
        # Get all stock (for initial cache)
        cursor.execute("""
            SELECT ms_party_id, item_name, measurement, 
                   total_inward, total_transfer_in, total_transfer_out, total_outward,
                   (total_inward + total_transfer_in - total_transfer_out - total_outward) as available_quantity
            FROM stock
            ORDER BY ms_party_id, item_name, measurement
        """)
        stock_records = cursor.fetchall()
        for stock in stock_records:
            stock['total_inward'] = float(stock.get('total_inward', 0))
            stock['total_transfer_in'] = float(stock.get('total_transfer_in', 0))
            stock['total_transfer_out'] = float(stock.get('total_transfer_out', 0))
            stock['total_outward'] = float(stock.get('total_outward', 0))
            stock['available_quantity'] = float(stock.get('available_quantity', 0))
        
        cursor.close()
        
        # Get last event ID
        last_event_id = get_last_event_id()
        
        return {
            "parties": parties,
            "stock": stock_records,
            "last_event_id": last_event_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Bootstrap snapshot error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/sync/events")
async def get_sync_events(
    request: Request,
    since_event_id: int = Query(0, description="Get events after this event_id")
):
    """
    Get incremental events since a given event_id (for reconnection sync).
    
    Query Parameters:
    - since_event_id: Event ID to start from (default: 0 = all events)
    
    Returns:
    {
        "events": [...],
        "last_event_id": 12345
    }
    """
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        events = get_events_since(since_event_id)
        last_event_id = get_last_event_id()
        
        return {
            "events": events,
            "last_event_id": last_event_id
        }
    except Exception as e:
        print(f"Sync events error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/stock/snapshot/{party_id}")
async def get_stock_snapshot(party_id: int, request: Request):
    """
    Get stock snapshot for a specific party (replaces repeated GET /api/stock/{party_id}).
    
    After this, clients should rely on WebSocket STOCK_DELTA_UPDATED events.
    
    Path Parameters:
    - party_id: Party ID
    
    Returns:
    {
        "party_id": 12,
        "stock": [
            {
                "item_name": "...",
                "measurement": 15,
                "available_quantity": 100,
                ...
            }
        ]
    }
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
        
        # Get stock for party
        cursor.execute("""
            SELECT item_name, measurement, 
                   total_inward, total_transfer_in, total_transfer_out, total_outward,
                   (total_inward + total_transfer_in - total_transfer_out - total_outward) as available_quantity
            FROM stock
            WHERE ms_party_id = %s
            ORDER BY item_name, measurement
        """, (party_id,))
        
        stock_records = cursor.fetchall()
        for stock in stock_records:
            stock['total_inward'] = float(stock.get('total_inward', 0))
            stock['total_transfer_in'] = float(stock.get('total_transfer_in', 0))
            stock['total_transfer_out'] = float(stock.get('total_transfer_out', 0))
            stock['total_outward'] = float(stock.get('total_outward', 0))
            stock['available_quantity'] = float(stock.get('available_quantity', 0))
        
        cursor.close()
        
        return {
            "party_id": party_id,
            "stock": stock_records
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Stock snapshot error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            db_pool.return_connection(conn)

