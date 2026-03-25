"""REST API Server for TMS Host"""

from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, List, Set
import time
import threading
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import secrets

from host.db_pool import db_pool
from host.stock_manager import (
    get_next_number, update_stock_for_inward, update_stock_for_transfer,
    update_stock_for_outward, get_stock_for_party, get_parties_with_stock
)
from common.security import hash_password, verify_password
from common.config import API_HOST, API_PORT

app = FastAPI(title="TMS API Server")

# Mount static files for web module
web_module_path = Path(__file__).parent.parent / "web_module"
if web_module_path.exists():
    app.mount("/static", StaticFiles(directory=str(web_module_path / "static")), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to handle invalid HTTP requests gracefully
@app.middleware("http")
async def handle_invalid_requests(request: Request, call_next):
    """Handle invalid HTTP requests gracefully to reduce warnings"""
    try:
        # Check if request path is valid
        if request.url.path.startswith("/favicon.ico") or request.url.path.startswith("/robots.txt"):
            from fastapi.responses import Response
            return Response(status_code=404)
        
        response = await call_next(request)
        return response
    except Exception as e:
        # Log but don't crash on invalid requests
        print(f"Request handling error (non-critical): {e}")
        from fastapi.responses import Response
        return Response(status_code=400, content="Bad Request")

# Rate limiting
rate_limit_store = defaultdict(list)
rate_limit_lock = threading.Lock()
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60  # seconds

# Session management for module authentication
module_sessions = {}  # {session_id: {"username": str, "role": str, "expires": datetime}}
module_sessions_lock = threading.Lock()
SESSION_TIMEOUT = timedelta(hours=24)  # 24 hour session


def rate_limit_check(client_ip: str) -> bool:
    """Check if client has exceeded rate limit"""
    with rate_limit_lock:
        now = time.time()
        # Clean old entries
        rate_limit_store[client_ip] = [
            req_time for req_time in rate_limit_store[client_ip]
            if now - req_time < RATE_LIMIT_WINDOW
        ]
        
        # Check limit
        if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
            return False
        
        # Add current request
        rate_limit_store[client_ip].append(now)
        return True


def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    return request.client.host if request.client else "unknown"


# Request models
class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: str
    role: str = "USER"


class UpdateUserRequest(BaseModel):
    user_id: int
    username: str
    email: str
    password: Optional[str] = None
    role: str = "USER"


class CreatePartyRequest(BaseModel):
    name: str
    rate_15_yards: float
    rate_22_yards: float
    discount_percent: float


class UpdatePartyRequest(BaseModel):
    party_id: int
    name: str
    rate_15_yards: float
    rate_22_yards: float
    discount_percent: float


class SimpleMasterCreateRequest(BaseModel):
    """Generic request model for name-only master creation."""
    name: str


class SimpleMasterUpdateRequest(BaseModel):
    """Generic request model for name-only master update."""
    id: int
    name: str


class SimpleMasterDeactivateRequest(BaseModel):
    """Generic request model for name-only master deactivation."""
    id: int


class InwardItem(BaseModel):
    item_name: str
    measurement: int
    quantity: float


class CreateInwardRequest(BaseModel):
    ms_party_id: int
    from_party: Optional[str] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    document_date: str
    items: List[InwardItem]
    created_by: str


class UpdateInwardRequest(BaseModel):
    inward_id: int
    ms_party_id: int
    from_party: Optional[str] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    document_date: str
    items: List[InwardItem]


class TransferItem(BaseModel):
    item_name: str
    measurement: int
    quantity: float


class CreateTransferRequest(BaseModel):
    ms_party_id: int
    from_party: Optional[str] = None
    transfer_to: Optional[str] = None
    transfer_to_ms_party_id: Optional[int] = None
    transfer_type: str = 'simple'  # 'simple' or 'by_name'
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    document_date: str
    items: List[TransferItem]
    created_by: str


class UpdateTransferRequest(BaseModel):
    transfer_id: int
    ms_party_id: int
    from_party: Optional[str] = None
    transfer_to: Optional[str] = None
    transfer_to_ms_party_id: Optional[int] = None
    transfer_type: str = 'simple'  # 'simple' or 'by_name'
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    document_date: str
    items: List[TransferItem]


class OutwardItem(BaseModel):
    item_name: str
    measurement: int
    quantity: float


class CreateOutwardRequest(BaseModel):
    ms_party_id: int
    from_party: Optional[str] = None
    outward_to: Optional[str] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    document_date: str
    items: List[OutwardItem]
    created_by: str


class UpdateOutwardRequest(BaseModel):
    outward_id: int
    ms_party_id: int
    from_party: Optional[str] = None
    outward_to: Optional[str] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    document_date: str
    items: List[OutwardItem]


class InvoiceItem(BaseModel):
    outward_document_id: Optional[int] = None  # For outward items
    transfer_document_id: Optional[int] = None  # For By Name Transfer items
    item_name: str
    measurement: int
    quantity: float
    rate: float
    amount: float


class CreateInvoiceRequest(BaseModel):
    ms_party_id: int
    outward_document_ids: List[int]  # List of outward IDs to include (for backward compatibility)
    items: List[InvoiceItem]
    discount_amount: float
    discount_source: str  # 'auto' or 'manual'
    invoice_date: str
    created_by: str


class UpdateInvoiceRequest(BaseModel):
    invoice_id: int
    ms_party_id: int
    outward_document_ids: List[int]  # List of outward IDs to include (for backward compatibility)
    items: List[InvoiceItem]
    discount_amount: float
    discount_source: str  # 'auto' or 'manual'
    invoice_date: str  # Invoice date in YYYY-MM-DD format


class VoucherDetailItem(BaseModel):
    party_id: Optional[int] = None
    asset_id: Optional[int] = None
    expense_id: Optional[int] = None
    vendor_id: Optional[int] = None
    debit_amount: Optional[float] = None
    credit_amount: Optional[float] = None


class CreateVoucherRequest(BaseModel):
    voucher_type: str  # CP, CR, or JV
    voucher_date: str
    description: Optional[str] = None
    details: List[VoucherDetailItem]


class UpdateVoucherRequest(BaseModel):
    voucher_id: int
    voucher_date: str
    description: Optional[str] = None
    details: List[VoucherDetailItem]


class LoginResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    role: Optional[str] = None
    username: Optional[str] = None
    user_id: Optional[int] = None
    modules: Optional[List[str]] = None




# Startup time
startup_time = time.time()

# WebSocket connection management
active_websockets: Set[WebSocket] = set()
websocket_lock = threading.Lock()


# ==================== WEBSOCKET ENDPOINTS ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time communication"""
    await websocket.accept()
    
    # Log client IP
    client_ip = websocket.client.host if websocket.client else "unknown"
    print(f"[SERVER] WebSocket connection from client IP: {client_ip}")
    
    # Add to active connections
    with websocket_lock:
        active_websockets.add(websocket)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": "WebSocket connection established"
        })
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for message from client (with timeout to allow periodic checks)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                try:
                    message = json.loads(data)
                    message_type = message.get("type", "unknown")
                    
                    # Handle different message types
                    if message_type == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        })
                    elif message_type == "subscribe":
                        # Client wants to subscribe to updates
                        await websocket.send_json({
                            "type": "subscribed",
                            "channels": message.get("channels", [])
                        })
                    elif message_type == "request_data":
                        # Client requests specific data
                        data_type = message.get("data_type")
                        if data_type == "health":
                            pool_health = db_pool.health_check()
                            uptime = time.time() - startup_time
                            await websocket.send_json({
                                "type": "data",
                                "data_type": "health",
                                "data": {
                                    "status": "ok",
                                    "uptime": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s",
                                    "db": "connected" if pool_health.get("status") == "healthy" else "disconnected",
                                    "pool": pool_health.get("status", "unknown")
                                }
                            })
                        else:
                            await websocket.send_json({
                                "type": "error",
                                "message": f"Unknown data type: {data_type}"
                            })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Unknown message type: {message_type}"
                        })
                        
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON format"
                    })
                    
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_json({
                    "type": "keepalive",
                    "timestamp": datetime.now().isoformat()
                })
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Remove from active connections
        with websocket_lock:
            active_websockets.discard(websocket)


async def broadcast_message(message: Dict):
    """Broadcast a message to all connected WebSocket clients"""
    if not active_websockets:
        return
    
    # Create a copy of the set to avoid modification during iteration
    with websocket_lock:
        websockets_to_send = list(active_websockets)
    
    disconnected = []
    for websocket in websockets_to_send:
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending WebSocket message: {e}")
            disconnected.append(websocket)
    
    # Remove disconnected websockets
    if disconnected:
        with websocket_lock:
            for ws in disconnected:
                active_websockets.discard(ws)


# ==================== REST API ENDPOINTS ====================

@app.get("/api/ping")
async def ping(request: Request):
    """Ping endpoint"""
    client_ip = get_client_ip(request)
    print(f"[SERVER] Ping from client IP: {client_ip}")
    return {"status": "pong", "timestamp": datetime.now().isoformat()}


@app.get("/api/health")
async def health(request: Request):
    """Health check endpoint"""
    client_ip = get_client_ip(request)
    print(f"[SERVER] Health check from client IP: {client_ip}")
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Check database pool
    pool_health = db_pool.health_check()
    
    uptime = time.time() - startup_time
    uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
    
    return {
        "status": "ok",
        "uptime": uptime_str,
        "db": "connected" if pool_health.get("status") == "healthy" else "disconnected",
        "pool": pool_health.get("status", "unknown")
    }


@app.post("/api/login", response_model=LoginResponse)
async def login(login_req: LoginRequest, request: Request):
    """User login endpoint"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, username, password_hash, role FROM users WHERE username = %s",
            (login_req.username,)
        )
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            return LoginResponse(success=False, message="Invalid credentials")
        
        if not verify_password(login_req.password, user["password_hash"]):
            return LoginResponse(success=False, message="Invalid credentials")
        
        # Generate simple token (in production, use JWT)
        import hashlib
        token = hashlib.sha256(
            f"{user['username']}{time.time()}".encode()
        ).hexdigest()
        
        # Fetch user modules
        cursor = conn.cursor()
        cursor.execute(
            "SELECT module_name FROM user_modules WHERE user_id = %s",
            (user["id"],)
        )
        user_modules = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        # Broadcast login event via WebSocket (if any clients connected)
        try:
            # Schedule broadcast in the event loop
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, create a new one for this task
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop and loop.is_running():
                asyncio.create_task(broadcast_message({
                    "type": "user_event",
                    "event": "login",
                    "username": user["username"],
                    "role": user["role"],
                    "timestamp": datetime.now().isoformat()
                }))
        except Exception as e:
            print(f"Error broadcasting login event: {e}")
        
        return LoginResponse(
            success=True,
            message="Login successful",
            token=token,
            role=user["role"],
            username=user["username"],
            user_id=user["id"],
            modules=user_modules
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/api/create-user")
async def create_user(user_req: CreateUserRequest, request: Request):
    """Create new user endpoint (admin only)"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Check if user exists
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id FROM users WHERE username = %s",
            (user_req.username,)
        )
        if cursor.fetchone():
            cursor.close()
            return {"success": False, "message": "Username already exists"}
        
        # Hash password
        password_hash = hash_password(user_req.password)
        
        # Insert user
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
            (user_req.username, password_hash, user_req.email, user_req.role)
        )
        conn.commit()
        cursor.close()
        
        return {"success": True, "message": "User created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create user error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/api/update-user")
async def update_user(user_req: UpdateUserRequest, request: Request):
    """Update user endpoint (admin only)"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_req.user_id,))
        if not cursor.fetchone():
            cursor.close()
            return {"success": False, "message": "User not found"}
        
        # Check if username is taken by another user
        cursor.execute(
            "SELECT id FROM users WHERE username = %s AND id != %s",
            (user_req.username, user_req.user_id)
        )
        if cursor.fetchone():
            cursor.close()
            return {"success": False, "message": "Username already taken"}
        
        # Update user
        if user_req.password:
            # Update with new password
            password_hash = hash_password(user_req.password)
            cursor.execute(
                "UPDATE users SET username = %s, email = %s, password_hash = %s, role = %s WHERE id = %s",
                (user_req.username, user_req.email, password_hash, user_req.role, user_req.user_id)
            )
        else:
            # Update without changing password
            cursor.execute(
                "UPDATE users SET username = %s, email = %s, role = %s WHERE id = %s",
                (user_req.username, user_req.email, user_req.role, user_req.user_id)
            )
        
        conn.commit()
        cursor.close()
        
        return {"success": True, "message": "User updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update user error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/parties")
async def get_parties(request: Request):
    """Get all MS liabilities (from Liabilities master module, uses parties table)"""
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
            SELECT id, name, rate_15_yards, rate_22_yards, discount_percent,
                   COALESCE(is_active, 1) as is_active,
                   created_at, updated_at
            FROM liabilities
            WHERE is_ms_party = TRUE
            ORDER BY is_active DESC, name
        """)
        parties = cursor.fetchall()
        
        # Convert decimal to float for JSON serialization
        for party in parties:
            party['rate_15_yards'] = float(party['rate_15_yards'])
            party['is_active'] = bool(party.get('is_active', True))
            party['rate_22_yards'] = float(party['rate_22_yards'])
            party['discount_percent'] = float(party['discount_percent'])
            if party['created_at']:
                party['created_at'] = party['created_at'].isoformat()
            if party['updated_at']:
                party['updated_at'] = party['updated_at'].isoformat()
        
        cursor.close()
        return {"success": True, "parties": parties}
        
    except Exception as e:
        print(f"Get parties error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/all-parties")
async def get_all_parties(request: Request):
    """Get all unique liability names from liabilities table (for autocomplete)"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor()
        
        # Get all unique liability names from liabilities table (MS liabilities + others)
        cursor.execute("""
            SELECT DISTINCT name as party_name FROM liabilities
            WHERE name IS NOT NULL AND name != ''
            ORDER BY party_name
        """)
        
        results = cursor.fetchall()
        all_parties = [row[0] for row in results if row[0]]  # Extract party names and filter out None/empty
        
        cursor.close()
        return {"success": True, "parties": all_parties}
        
    except Exception as e:
        print(f"Get all parties error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


class SavePartyNameRequest(BaseModel):
    party_name: str


@app.post("/api/save-party-name")
async def save_party_name(party_req: SavePartyNameRequest, request: Request):
    """Save a liability/party name if it doesn't exist (for From Party, Transfer To, Outward To fields)"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        party_name = party_req.party_name.strip()
        if not party_name:
            raise HTTPException(status_code=400, detail="Party name cannot be empty")
        
        cursor = conn.cursor(dictionary=True)
        
        # Check if party already exists
        cursor.execute("SELECT id FROM liabilities WHERE name = %s", (party_name,))
        existing = cursor.fetchone()
        
        if existing:
            # Party already exists
            cursor.close()
            return {"success": True, "message": "Party already exists", "party_id": existing['id']}
        
        # Insert new liability (not an MS liability, just a name for autocomplete)
        cursor.execute("""
            INSERT INTO liabilities (name, is_ms_party, rate_15_yards, rate_22_yards, discount_percent)
            VALUES (%s, FALSE, 0.00, 0.00, 0.00)
        """, (party_name,))
        
        conn.commit()
        party_id = cursor.lastrowid
        cursor.close()
        
        return {"success": True, "message": "Party name saved", "party_id": party_id}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Save party name error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/parties/{party_id}/changelog")
async def get_party_changelog(party_id: int, request: Request):
    """Get changelog for a liability (party)"""
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
            SELECT id, change_date, changes
            FROM liability_changelog
            WHERE party_id = %s
            ORDER BY change_date DESC
        """, (party_id,))
        changelog = cursor.fetchall()
        
        # Convert datetime to string
        for entry in changelog:
            if entry['change_date']:
                entry['change_date'] = entry['change_date'].isoformat()
        
        cursor.close()
        return {"success": True, "changelog": changelog}
        
    except Exception as e:
        print(f"Get changelog error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/api/parties")
async def create_party(party_req: CreatePartyRequest, request: Request):
    """Create a new liability (stored in parties table)"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor()
        
        # Check if liability name already exists
        cursor.execute("SELECT id FROM liabilities WHERE name = %s", (party_req.name,))
        if cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=400, detail="Liability name already exists")
        
        # Insert liability (MS liability from master module)
        cursor.execute("""
            INSERT INTO liabilities (name, rate_15_yards, rate_22_yards, discount_percent, is_ms_party)
            VALUES (%s, %s, %s, %s, TRUE)
        """, (party_req.name, party_req.rate_15_yards, party_req.rate_22_yards, party_req.discount_percent))
        
        party_id = cursor.lastrowid
        
        # Create initial changelog entry
        cursor.execute("""
            INSERT INTO liability_changelog (party_id, changes)
            VALUES (%s, %s)
        """, (party_id, f"Liability created: {party_req.name}"))
        
        # Auto-create stock ledger for this liability party
        cursor.execute("""
            INSERT INTO stock_ledgers (party_id, ledger_name, is_ud_ledger)
            VALUES (%s, %s, FALSE)
        """, (party_id, party_req.name))

        # Auto-create financial ledger for this liability party
        cursor.execute("""
            INSERT INTO financial_ledgers (party_id, name, is_default)
            VALUES (%s, %s, FALSE)
        """, (party_id, party_req.name))
        
        conn.commit()
        cursor.close()

        # Fetch created liability (for instant UI updates on clients)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, rate_15_yards, rate_22_yards, discount_percent,
                   created_at, updated_at
            FROM liabilities
            WHERE id = %s
        """, (party_id,))
        party = cursor.fetchone()
        cursor.close()

        if party:
            party['rate_15_yards'] = float(party['rate_15_yards'])
            party['rate_22_yards'] = float(party['rate_22_yards'])
            party['discount_percent'] = float(party['discount_percent'])
            if party.get('created_at'):
                party['created_at'] = party['created_at'].isoformat()
            if party.get('updated_at'):
                party['updated_at'] = party['updated_at'].isoformat()

        # Broadcast real-time event (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "party",
                "action": "created",
                "data": party or {"id": party_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting party created: {e}")

        return {"success": True, "message": "Liability created successfully", "party_id": party_id, "party": party}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create party error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.put("/api/parties")
async def update_party(party_req: UpdatePartyRequest, request: Request):
    """Update an existing liability (stored in parties table)"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        
        # Get current liability data
        cursor.execute("""
            SELECT name, rate_15_yards, rate_22_yards, discount_percent
            FROM liabilities WHERE id = %s
        """, (party_req.party_id,))
        old_party = cursor.fetchone()
        
        if not old_party:
            cursor.close()
            raise HTTPException(status_code=404, detail="Liability not found")
        
        # Check if new name conflicts with another liability
        cursor.execute("SELECT id FROM liabilities WHERE name = %s AND id != %s", 
                      (party_req.name, party_req.party_id))
        if cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=400, detail="Liability name already exists")
        
        # Build changelog entry
        changes = []
        if old_party['name'] != party_req.name:
            changes.append(f"Name: '{old_party['name']}' → '{party_req.name}'")
        if float(old_party['rate_15_yards']) != party_req.rate_15_yards:
            changes.append(f"15 Yards Rate: {old_party['rate_15_yards']} → {party_req.rate_15_yards}")
        if float(old_party['rate_22_yards']) != party_req.rate_22_yards:
            changes.append(f"22 Yards Rate: {old_party['rate_22_yards']} → {party_req.rate_22_yards}")
        if float(old_party['discount_percent']) != party_req.discount_percent:
            changes.append(f"Discount %: {old_party['discount_percent']} → {party_req.discount_percent}")
        
        # Update liability
        cursor.execute("""
            UPDATE liabilities
            SET name = %s, rate_15_yards = %s, rate_22_yards = %s, discount_percent = %s
            WHERE id = %s
        """, (party_req.name, party_req.rate_15_yards, party_req.rate_22_yards, 
              party_req.discount_percent, party_req.party_id))
        
        # Add changelog entry if there were changes
        if changes:
            cursor.execute("""
                INSERT INTO liability_changelog (party_id, changes)
                VALUES (%s, %s)
            """, (party_req.party_id, " | ".join(changes)))
        
        conn.commit()
        cursor.close()

        # Fetch updated liability (for instant UI updates on clients)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, rate_15_yards, rate_22_yards, discount_percent,
                   created_at, updated_at
            FROM liabilities
            WHERE id = %s
        """, (party_req.party_id,))
        party = cursor.fetchone()
        cursor.close()

        if party:
            party['rate_15_yards'] = float(party['rate_15_yards'])
            party['rate_22_yards'] = float(party['rate_22_yards'])
            party['discount_percent'] = float(party['discount_percent'])
            if party.get('created_at'):
                party['created_at'] = party['created_at'].isoformat()
            if party.get('updated_at'):
                party['updated_at'] = party['updated_at'].isoformat()

        # Broadcast real-time event (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "party",
                "action": "updated",
                "data": party or {"id": party_req.party_id},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting party updated: {e}")

        return {"success": True, "message": "Liability updated successfully", "party": party}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update party error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.delete("/api/parties/{party_id}")
async def delete_party(party_id: int, request: Request):
    """Soft-delete a liability: mark as inactive (does not remove from database)"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        
        # Check if liability exists
        cursor.execute("SELECT id, name, is_active FROM liabilities WHERE id = %s", (party_id,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            raise HTTPException(status_code=404, detail="Liability not found")
        
        if not row.get('is_active', True):
            cursor.close()
            raise HTTPException(status_code=400, detail="This party is already inactive.")
        
        # Soft delete: mark as inactive (no hard delete, so no foreign key issues)
        cursor.execute("UPDATE liabilities SET is_active = FALSE WHERE id = %s", (party_id,))
        
        conn.commit()
        cursor.close()

        # Broadcast real-time event (best-effort)
        try:
            await broadcast_message({
                "type": "entity_change",
                "entity": "party",
                "action": "deactivated",
                "data": {"id": party_id, "is_active": False},
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error broadcasting party deactivated: {e}")

        return {"success": True, "message": "Liability marked as inactive", "party_id": party_id}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete party error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


# ==================== SIMPLE NAME-ONLY MASTER MODULES ====================

def _get_username_from_request(request: Request) -> str:
    """Extract username from request headers, defaulting to 'SYSTEM'."""
    username = request.headers.get("X-Username") or request.headers.get("x-username")
    return username or "SYSTEM"


@app.get("/api/assets")
async def get_assets(request: Request):
    """
    Get all Assets master records.

    Each Asset is a name-only master, with audit fields:
    - created_at, created_by
    - updated_at, updated_by
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
        cursor.execute(
            """
            SELECT id, name, is_active, created_at, updated_at, created_by, updated_by
            FROM assets
            ORDER BY name
            """
        )
        assets = cursor.fetchall()

        for row in assets:
            if row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat()
            if row.get("updated_at"):
                row["updated_at"] = row["updated_at"].isoformat()

        cursor.close()
        return {"success": True, "assets": assets}
    except Exception as e:
        print(f"Get assets error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/api/assets")
async def create_asset(asset_req: SimpleMasterCreateRequest, request: Request):
    """
    Create a new Asset master record.

    Name-only; no balances, quantities, or transactional logic.
    """
    client_ip = get_client_ip(request)

    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    conn = None
    try:
        username = _get_username_from_request(request)
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")

        cursor = conn.cursor()

        cursor.execute("SELECT id FROM assets WHERE name = %s", (asset_req.name,))
        if cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=400, detail="Asset name already exists")

        cursor.execute(
            """
            INSERT INTO assets (name, is_active, created_by, updated_by)
            VALUES (%s, TRUE, %s, %s)
            """,
            (asset_req.name, username, username),
        )
        asset_id = cursor.lastrowid
        conn.commit()
        cursor.close()

        return {"success": True, "message": "Asset created successfully", "id": asset_id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create asset error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.put("/api/assets")
async def update_asset(asset_req: SimpleMasterUpdateRequest, request: Request):
    """
    Update an existing Asset master name.

    No financial or quantity updates are performed here.
    """
    client_ip = get_client_ip(request)

    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    conn = None
    try:
        username = _get_username_from_request(request)
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")

        cursor = conn.cursor()

        cursor.execute("SELECT id FROM assets WHERE id = %s", (asset_req.id,))
        if not cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=404, detail="Asset not found")

        cursor.execute(
            "SELECT id FROM assets WHERE name = %s AND id != %s",
            (asset_req.name, asset_req.id),
        )
        if cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=400, detail="Asset name already exists")

        cursor.execute(
            """
            UPDATE assets
            SET name = %s, updated_by = %s
            WHERE id = %s
            """,
            (asset_req.name, username, asset_req.id),
        )

        conn.commit()
        cursor.close()
        return {"success": True, "message": "Asset updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update asset error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.put("/api/assets/deactivate")
async def deactivate_asset(asset_req: SimpleMasterDeactivateRequest, request: Request):
    """
    Deactivate an Asset master record.

    Deactivation is non-destructive and has no accounting impact.
    """
    client_ip = get_client_ip(request)

    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    conn = None
    try:
        username = _get_username_from_request(request)
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")

        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE id = %s", (asset_req.id,))
        if not cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=404, detail="Asset not found")

        cursor.execute(
            """
            UPDATE assets
            SET is_active = FALSE, updated_by = %s
            WHERE id = %s
            """,
            (username, asset_req.id),
        )
        conn.commit()
        cursor.close()
        return {"success": True, "message": "Asset deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Deactivate asset error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/expenses")
async def get_expenses(request: Request):
    """
    Get all Expenses master records (name-only).

    Includes audit fields for created/updated date and user.
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
        cursor.execute(
            """
            SELECT id, name, is_active, created_at, updated_at, created_by, updated_by
            FROM expenses
            ORDER BY name
            """
        )
        expenses = cursor.fetchall()

        for row in expenses:
            if row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat()
            if row.get("updated_at"):
                row["updated_at"] = row["updated_at"].isoformat()

        cursor.close()
        return {"success": True, "expenses": expenses}
    except Exception as e:
        print(f"Get expenses error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/api/expenses")
async def create_expense(exp_req: SimpleMasterCreateRequest, request: Request):
    """Create a new Expense name (no posting or voucher logic)."""
    client_ip = get_client_ip(request)

    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    conn = None
    try:
        username = _get_username_from_request(request)
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")

        cursor = conn.cursor()
        cursor.execute("SELECT id FROM expenses WHERE name = %s", (exp_req.name,))
        if cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=400, detail="Expense name already exists")

        cursor.execute(
            """
            INSERT INTO expenses (name, is_active, created_by, updated_by)
            VALUES (%s, TRUE, %s, %s)
            """,
            (exp_req.name, username, username),
        )
        expense_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        return {"success": True, "message": "Expense created successfully", "id": expense_id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create expense error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.put("/api/expenses")
async def update_expense(exp_req: SimpleMasterUpdateRequest, request: Request):
    """Update an existing Expense master name."""
    client_ip = get_client_ip(request)

    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    conn = None
    try:
        username = _get_username_from_request(request)
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")

        cursor = conn.cursor()
        cursor.execute("SELECT id FROM expenses WHERE id = %s", (exp_req.id,))
        if not cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=404, detail="Expense not found")

        cursor.execute(
            "SELECT id FROM expenses WHERE name = %s AND id != %s",
            (exp_req.name, exp_req.id),
        )
        if cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=400, detail="Expense name already exists")

        cursor.execute(
            """
            UPDATE expenses
            SET name = %s, updated_by = %s
            WHERE id = %s
            """,
            (exp_req.name, username, exp_req.id),
        )
        conn.commit()
        cursor.close()
        return {"success": True, "message": "Expense updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update expense error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.put("/api/expenses/deactivate")
async def deactivate_expense(exp_req: SimpleMasterDeactivateRequest, request: Request):
    """Deactivate an Expense master name (no accounting impact)."""
    client_ip = get_client_ip(request)

    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    conn = None
    try:
        username = _get_username_from_request(request)
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")

        cursor = conn.cursor()
        cursor.execute("SELECT id FROM expenses WHERE id = %s", (exp_req.id,))
        if not cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=404, detail="Expense not found")

        cursor.execute(
            """
            UPDATE expenses
            SET is_active = FALSE, updated_by = %s
            WHERE id = %s
            """,
            (username, exp_req.id),
        )
        conn.commit()
        cursor.close()
        return {"success": True, "message": "Expense deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Deactivate expense error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/vendors")
async def get_vendors(request: Request):
    """
    Get all Vendors master records (name-only).

    Includes created/updated dates and user information for audit trail.
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
        cursor.execute(
            """
            SELECT id, name, is_active, created_at, updated_at, created_by, updated_by
            FROM vendors
            ORDER BY name
            """
        )
        vendors = cursor.fetchall()

        for row in vendors:
            if row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat()
            if row.get("updated_at"):
                row["updated_at"] = row["updated_at"].isoformat()

        cursor.close()
        return {"success": True, "vendors": vendors}
    except Exception as e:
        print(f"Get vendors error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/api/vendors")
async def create_vendor(vendor_req: SimpleMasterCreateRequest, request: Request):
    """Create a new Vendor master name (no ledger impact)."""
    client_ip = get_client_ip(request)

    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    conn = None
    try:
        username = _get_username_from_request(request)
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")

        cursor = conn.cursor()
        cursor.execute("SELECT id FROM vendors WHERE name = %s", (vendor_req.name,))
        if cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=400, detail="Vendor name already exists")

        cursor.execute(
            """
            INSERT INTO vendors (name, is_active, created_by, updated_by)
            VALUES (%s, TRUE, %s, %s)
            """,
            (vendor_req.name, username, username),
        )
        vendor_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        return {"success": True, "message": "Vendor created successfully", "id": vendor_id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create vendor error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.put("/api/vendors")
async def update_vendor(vendor_req: SimpleMasterUpdateRequest, request: Request):
    """Update an existing Vendor master name."""
    client_ip = get_client_ip(request)

    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    conn = None
    try:
        username = _get_username_from_request(request)
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")

        cursor = conn.cursor()
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_req.id,))
        if not cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=404, detail="Vendor not found")

        cursor.execute(
            "SELECT id FROM vendors WHERE name = %s AND id != %s",
            (vendor_req.name, vendor_req.id),
        )
        if cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=400, detail="Vendor name already exists")

        cursor.execute(
            """
            UPDATE vendors
            SET name = %s, updated_by = %s
            WHERE id = %s
            """,
            (vendor_req.name, username, vendor_req.id),
        )
        conn.commit()
        cursor.close()
        return {"success": True, "message": "Vendor updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update vendor error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.put("/api/vendors/deactivate")
async def deactivate_vendor(vendor_req: SimpleMasterDeactivateRequest, request: Request):
    """Deactivate a Vendor master name (no accounting impact)."""
    client_ip = get_client_ip(request)

    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    conn = None
    try:
        username = _get_username_from_request(request)
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")

        cursor = conn.cursor()
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_req.id,))
        if not cursor.fetchone():
            cursor.close()
            raise HTTPException(status_code=404, detail="Vendor not found")

        cursor.execute(
            """
            UPDATE vendors
            SET is_active = FALSE, updated_by = %s
            WHERE id = %s
            """,
            (username, vendor_req.id),
        )
        conn.commit()
        cursor.close()
        return {"success": True, "message": "Vendor deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Deactivate vendor error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


# ==================== STOCK ENDPOINTS ====================

@app.get("/api/stock/parties")
async def get_parties_with_stock_endpoint(request: Request):
    """Get list of parties with available stock"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        parties = get_parties_with_stock()
        return {"success": True, "parties": parties}
    except Exception as e:
        print(f"Get parties with stock error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/stock/{party_id}")
async def get_stock(party_id: int, request: Request):
    """Get stock for a specific party"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        stock = get_stock_for_party(party_id)
        return {"success": True, "stock": stock}
    except Exception as e:
        print(f"Get stock error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/stock/{party_id}/available")
async def get_available_stock(party_id: int, request: Request):
    """Get available stock for a party (for transfer/outward validation) - includes negative stock"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        stock = get_stock_for_party(party_id)
        # Return all stock items, including negative values
        return {"success": True, "stock": stock}
    except Exception as e:
        print(f"Get available stock error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== STOCK LEDGERS ENDPOINTS ====================

@app.get("/api/stock-ledgers")
async def get_stock_ledgers(request: Request):
    """Get all stock ledgers (UD + all party ledgers)"""
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
            SELECT sl.id, sl.ledger_name, sl.is_ud_ledger, sl.party_id,
                   l.name as party_name
            FROM stock_ledgers sl
            LEFT JOIN liabilities l ON sl.party_id = l.id
            ORDER BY sl.is_ud_ledger DESC, sl.ledger_name ASC
        """)
        ledgers = cursor.fetchall()
        cursor.close()
        
        return {"success": True, "ledgers": ledgers}
    except Exception as e:
        print(f"Get stock ledgers error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/stock-ledgers/{ledger_id}/entries")
async def get_ledger_entries(ledger_id: int, request: Request):
    """Get all entries for a specific ledger"""
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
            SELECT id, entry_date, transaction_type, transaction_number,
                   particulars, description, item_name, qty_15_yards, qty_22_yards,
                   total_qty_debit, total_qty_credit, balance
            FROM stock_ledger_entries
            WHERE ledger_id = %s
            ORDER BY entry_date ASC, id ASC
        """, (ledger_id,))
        entries = cursor.fetchall()
        cursor.close()
        
        # Convert decimals to floats
        for entry in entries:
            entry['qty_15_yards'] = float(entry.get('qty_15_yards', 0))
            entry['qty_22_yards'] = float(entry.get('qty_22_yards', 0))
            entry['total_qty_debit'] = float(entry.get('total_qty_debit', 0))
            entry['total_qty_credit'] = float(entry.get('total_qty_credit', 0))
            entry['balance'] = float(entry.get('balance', 0))
            if entry.get('entry_date'):
                entry['entry_date'] = entry['entry_date'].isoformat() if hasattr(entry['entry_date'], 'isoformat') else str(entry['entry_date'])
        
        return {"success": True, "entries": entries}
    except Exception as e:
        print(f"Get ledger entries error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/stock-ledgers/search")
async def search_ledgers(search_term: str = "", request: Request = None):
    """Search ledgers by party name"""
    if request is None:
        from fastapi import Request as Req
        request = Req
    
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        if search_term:
            cursor.execute("""
                SELECT sl.id, sl.ledger_name, sl.is_ud_ledger, sl.party_id,
                       l.name as party_name
                FROM stock_ledgers sl
                LEFT JOIN liabilities l ON sl.party_id = l.id
                WHERE sl.ledger_name LIKE %s OR l.name LIKE %s
                ORDER BY sl.is_ud_ledger DESC, sl.ledger_name ASC
            """, (f"%{search_term}%", f"%{search_term}%"))
        else:
            cursor.execute("""
                SELECT sl.id, sl.ledger_name, sl.is_ud_ledger, sl.party_id,
                       l.name as party_name
                FROM stock_ledgers sl
                LEFT JOIN liabilities l ON sl.party_id = l.id
                ORDER BY sl.is_ud_ledger DESC, sl.ledger_name ASC
            """)
        ledgers = cursor.fetchall()
        cursor.close()
        
        return {"success": True, "ledgers": ledgers}
    except Exception as e:
        print(f"Search ledgers error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


# ==================== FINANCIAL LEDGERS ENDPOINTS ====================

@app.get("/api/financial-ledgers")
async def get_financial_ledgers(request: Request):
    """Get all financial ledgers, ensuring assets have ledgers"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        
        # Ensure financial ledgers exist for all assets
        cursor.execute("""
            SELECT a.id, a.name 
            FROM assets a
            WHERE a.is_active = TRUE
            AND a.name NOT IN (SELECT name FROM financial_ledgers WHERE name = a.name)
        """)
        assets_without_ledgers = cursor.fetchall()
        
        for asset in assets_without_ledgers:
            try:
                cursor.execute("""
                    INSERT INTO financial_ledgers (name, party_id, is_default)
                    VALUES (%s, NULL, FALSE)
                """, (asset['name'],))
            except Exception as e:
                # Ledger might have been created by another request, ignore
                pass
        
        # Ensure financial ledgers exist for all expenses
        cursor.execute("""
            SELECT e.id, e.name 
            FROM expenses e
            WHERE e.is_active = TRUE
            AND e.name NOT IN (SELECT name FROM financial_ledgers WHERE name = e.name)
        """)
        expenses_without_ledgers = cursor.fetchall()
        
        for expense in expenses_without_ledgers:
            try:
                cursor.execute("""
                    INSERT INTO financial_ledgers (name, party_id, is_default)
                    VALUES (%s, NULL, FALSE)
                """, (expense['name'],))
            except Exception as e:
                # Ledger might have been created by another request, ignore
                pass
        
        # Ensure financial ledgers exist for all vendors
        cursor.execute("""
            SELECT v.id, v.name 
            FROM vendors v
            WHERE v.is_active = TRUE
            AND v.name NOT IN (SELECT name FROM financial_ledgers WHERE name = v.name)
        """)
        vendors_without_ledgers = cursor.fetchall()
        
        for vendor in vendors_without_ledgers:
            try:
                cursor.execute("""
                    INSERT INTO financial_ledgers (name, party_id, is_default)
                    VALUES (%s, NULL, FALSE)
                """, (vendor['name'],))
            except Exception as e:
                # Ledger might have been created by another request, ignore
                pass
        
        if assets_without_ledgers or expenses_without_ledgers or vendors_without_ledgers:
            conn.commit()
        
        # Get all financial ledgers
        cursor.execute("""
            SELECT id, name, party_id, is_default
            FROM financial_ledgers
            ORDER BY is_default DESC, name ASC
        """)
        ledgers = cursor.fetchall()
        cursor.close()
        
        return {"success": True, "ledgers": ledgers}
    except Exception as e:
        print(f"Get financial ledgers error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/financial-ledgers/{ledger_id}/entries")
async def get_financial_ledger_entries(ledger_id: int, request: Request):
    """Get all entries for a specific financial ledger"""
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
            SELECT id, entry_date, particulars, invoice_number, voucher_number,
                   description, debit, credit, balance
            FROM financial_ledger_entries
            WHERE ledger_id = %s
            ORDER BY entry_date ASC, id ASC
        """, (ledger_id,))
        entries = cursor.fetchall()
        cursor.close()
        
        # Convert decimals to floats and dates to strings
        for entry in entries:
            entry['debit'] = float(entry.get('debit', 0) or 0)
            entry['credit'] = float(entry.get('credit', 0) or 0)
            entry['balance'] = float(entry.get('balance', 0) or 0)
            if entry.get('entry_date'):
                entry['entry_date'] = entry['entry_date'].isoformat() if hasattr(entry['entry_date'], 'isoformat') else str(entry['entry_date'])
        
        return {"success": True, "entries": entries}
    except Exception as e:
        print(f"Get financial ledger entries error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/vouchers/descriptions")
async def get_voucher_descriptions(request: Request):
    """Get unique descriptions from all vouchers for autocomplete"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT description
            FROM voucher_master
            WHERE description IS NOT NULL AND description != ''
            ORDER BY description ASC
        """)
        
        descriptions = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        return {"success": True, "descriptions": descriptions}
    except Exception as e:
        print(f"Get voucher descriptions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/vouchers")
async def get_vouchers(request: Request, voucher_type: Optional[str] = None):
    """Get all vouchers, optionally filtered by type"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        
        if voucher_type:
            cursor.execute("""
                SELECT id, voucher_no, voucher_type, voucher_date, description, total_amount,
                       created_by, edited_by, edit_log_history, created_at, updated_at
                FROM voucher_master
                WHERE voucher_type = %s
                ORDER BY voucher_date DESC, id DESC
            """, (voucher_type,))
        else:
            cursor.execute("""
                SELECT id, voucher_no, voucher_type, voucher_date, description, total_amount,
                       created_by, edited_by, edit_log_history, created_at, updated_at
                FROM voucher_master
                ORDER BY voucher_date DESC, id DESC
            """)
        
        vouchers = cursor.fetchall()
        cursor.close()
        
        # Convert dates and decimals
        for voucher in vouchers:
            if voucher.get('voucher_date'):
                voucher['voucher_date'] = voucher['voucher_date'].isoformat() if hasattr(voucher['voucher_date'], 'isoformat') else str(voucher['voucher_date'])
            if voucher.get('created_at'):
                voucher['created_at'] = voucher['created_at'].isoformat() if hasattr(voucher['created_at'], 'isoformat') else str(voucher['created_at'])
            if voucher.get('updated_at'):
                voucher['updated_at'] = voucher['updated_at'].isoformat() if hasattr(voucher['updated_at'], 'isoformat') else str(voucher['updated_at'])
            voucher['total_amount'] = float(voucher.get('total_amount', 0) or 0)
        
        return {"success": True, "vouchers": vouchers}
    except Exception as e:
        print(f"Get vouchers error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/vouchers/{voucher_id}")
async def get_voucher(voucher_id: int, request: Request):
    """Get a single voucher with its details"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        
        # Get voucher master
        cursor.execute("""
            SELECT id, voucher_no, voucher_type, voucher_date, description, total_amount,
                   created_by, edited_by, edit_log_history, created_at, updated_at
            FROM voucher_master
            WHERE id = %s
        """, (voucher_id,))
        voucher = cursor.fetchone()
        
        if not voucher:
            raise HTTPException(status_code=404, detail="Voucher not found")
        
        # Get voucher details with account names
        cursor.execute("""
            SELECT vd.id, vd.party_id, vd.asset_id, vd.expense_id, vd.vendor_id, 
                   vd.debit_amount, vd.credit_amount,
                   l.name as party_name,
                   a.name as asset_name,
                   e.name as expense_name,
                   v.name as vendor_name
            FROM voucher_detail vd
            LEFT JOIN liabilities l ON vd.party_id = l.id
            LEFT JOIN assets a ON vd.asset_id = a.id
            LEFT JOIN expenses e ON vd.expense_id = e.id
            LEFT JOIN vendors v ON vd.vendor_id = v.id
            WHERE vd.voucher_id = %s
            ORDER BY vd.id ASC
        """, (voucher_id,))
        details = cursor.fetchall()
        cursor.close()
        
        # Convert dates and decimals
        if voucher.get('voucher_date'):
            voucher['voucher_date'] = voucher['voucher_date'].isoformat() if hasattr(voucher['voucher_date'], 'isoformat') else str(voucher['voucher_date'])
        if voucher.get('created_at'):
            voucher['created_at'] = voucher['created_at'].isoformat() if hasattr(voucher['created_at'], 'isoformat') else str(voucher['created_at'])
        if voucher.get('updated_at'):
            voucher['updated_at'] = voucher['updated_at'].isoformat() if hasattr(voucher['updated_at'], 'isoformat') else str(voucher['updated_at'])
        voucher['total_amount'] = float(voucher.get('total_amount', 0) or 0)
        
        for detail in details:
            detail['debit_amount'] = float(detail['debit_amount']) if detail['debit_amount'] else None
            detail['credit_amount'] = float(detail['credit_amount']) if detail['credit_amount'] else None
        
        voucher['details'] = details
        return {"success": True, "voucher": voucher}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get voucher error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/api/vouchers")
async def create_voucher(voucher_req: CreateVoucherRequest, request: Request):
    """Create a new voucher"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    if voucher_req.voucher_type not in ['CP', 'CR', 'JV']:
        raise HTTPException(status_code=400, detail="Invalid voucher type. Must be CP, CR, or JV")
    
    if not voucher_req.details:
        raise HTTPException(status_code=400, detail="Voucher must have at least one detail entry")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Validate debit/credit totals
        total_debit = sum(d.debit_amount or 0 for d in voucher_req.details)
        total_credit = sum(d.credit_amount or 0 for d in voucher_req.details)
        
        if abs(total_debit - total_credit) > 0.01:  # Allow small floating point differences
            raise HTTPException(status_code=400, detail=f"Debit total ({total_debit}) must equal credit total ({total_credit})")
        
        # Validate CP/CR constraints
        if voucher_req.voucher_type in ['CP', 'CR']:
            asset_count = sum(1 for d in voucher_req.details if d.asset_id)
            if asset_count != 1:
                raise HTTPException(status_code=400, detail=f"{voucher_req.voucher_type} voucher must have exactly one cash (asset) account")
        
        cursor = conn.cursor()
        
        # Get username from request headers
        created_by = _get_username_from_request(request)
        
        # Generate voucher number
        from host.voucher_manager import get_next_voucher_number
        voucher_no = get_next_voucher_number(voucher_req.voucher_type, conn)
        
        # Insert voucher master
        cursor.execute("""
            INSERT INTO voucher_master (voucher_no, voucher_type, voucher_date, description, total_amount, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (voucher_no, voucher_req.voucher_type, voucher_req.voucher_date, voucher_req.description, total_debit, created_by))
        
        voucher_id = cursor.lastrowid
        
        # Insert voucher details
        for detail in voucher_req.details:
            cursor.execute("""
                INSERT INTO voucher_detail (voucher_id, party_id, asset_id, expense_id, vendor_id, debit_amount, credit_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (voucher_id, detail.party_id, detail.asset_id, detail.expense_id, detail.vendor_id, detail.debit_amount, detail.credit_amount))
        
        # Post to ledgers
        from host.voucher_manager import post_voucher_to_ledgers
        if not post_voucher_to_ledgers(voucher_id, conn):
            conn.rollback()
            raise HTTPException(status_code=500, detail="Failed to post voucher to ledgers")
        
        conn.commit()
        cursor.close()
        
        return {"success": True, "voucher_id": voucher_id, "voucher_no": voucher_no}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"Create voucher error: {e}")
        print(f"Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.put("/api/vouchers/{voucher_id}")
async def update_voucher(voucher_id: int, voucher_req: UpdateVoucherRequest, request: Request):
    """Update an existing voucher"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    if voucher_id != voucher_req.voucher_id:
        raise HTTPException(status_code=400, detail="Voucher ID mismatch")
    
    if not voucher_req.details:
        raise HTTPException(status_code=400, detail="Voucher must have at least one detail entry")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        
        # Get existing voucher with all fields for edit log
        cursor.execute("""
            SELECT id, voucher_no, voucher_type, voucher_date, description, total_amount, created_by, edited_by, edit_log_history
            FROM voucher_master WHERE id = %s
        """, (voucher_id,))
        existing = cursor.fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Voucher not found")
        
        voucher_no = existing['voucher_no']
        voucher_type = existing['voucher_type']
        
        # Get old voucher details for edit log
        cursor.execute("""
            SELECT id, party_id, asset_id, expense_id, vendor_id, debit_amount, credit_amount
            FROM voucher_detail
            WHERE voucher_id = %s
        """, (voucher_id,))
        old_details = cursor.fetchall()
        
        # Validate debit/credit totals
        total_debit = sum(d.debit_amount or 0 for d in voucher_req.details)
        total_credit = sum(d.credit_amount or 0 for d in voucher_req.details)
        
        if abs(total_debit - total_credit) > 0.01:
            raise HTTPException(status_code=400, detail=f"Debit total ({total_debit}) must equal credit total ({total_credit})")
        
        # Validate CP/CR constraints
        if voucher_type in ['CP', 'CR']:
            asset_count = sum(1 for d in voucher_req.details if d.asset_id)
            if asset_count != 1:
                raise HTTPException(status_code=400, detail=f"{voucher_type} voucher must have exactly one cash (asset) account")
        
        # Get username from request headers
        edited_by = _get_username_from_request(request)
        
        # Prepare new voucher data for edit log
        new_doc = {
            'voucher_type': voucher_type,
            'voucher_date': voucher_req.voucher_date,
            'description': voucher_req.description or '',
            'total_amount': total_debit
        }
        
        # Prepare new details for edit log
        new_details = []
        for detail in voucher_req.details:
            new_details.append({
                'party_id': detail.party_id,
                'asset_id': detail.asset_id,
                'expense_id': detail.expense_id,
                'vendor_id': detail.vendor_id,
                'debit_amount': detail.debit_amount,
                'credit_amount': detail.credit_amount
            })
        
        # Get account names for edit log
        party_ids = set()
        asset_ids = set()
        expense_ids = set()
        vendor_ids = set()
        
        for detail in old_details + new_details:
            if detail.get('party_id'):
                party_ids.add(detail['party_id'])
            if detail.get('asset_id'):
                asset_ids.add(detail['asset_id'])
            if detail.get('expense_id'):
                expense_ids.add(detail['expense_id'])
            if detail.get('vendor_id'):
                vendor_ids.add(detail['vendor_id'])
        
        party_names = {}
        if party_ids:
            placeholders = ','.join(['%s'] * len(party_ids))
            cursor.execute(f"SELECT id, name FROM liabilities WHERE id IN ({placeholders})", tuple(party_ids))
            for row in cursor.fetchall():
                party_names[row['id']] = row['name']
        
        asset_names = {}
        if asset_ids:
            placeholders = ','.join(['%s'] * len(asset_ids))
            cursor.execute(f"SELECT id, name FROM assets WHERE id IN ({placeholders})", tuple(asset_ids))
            for row in cursor.fetchall():
                asset_names[row['id']] = row['name']
        
        expense_names = {}
        if expense_ids:
            placeholders = ','.join(['%s'] * len(expense_ids))
            cursor.execute(f"SELECT id, name FROM expenses WHERE id IN ({placeholders})", tuple(expense_ids))
            for row in cursor.fetchall():
                expense_names[row['id']] = row['name']
        
        vendor_names = {}
        if vendor_ids:
            placeholders = ','.join(['%s'] * len(vendor_ids))
            cursor.execute(f"SELECT id, name FROM vendors WHERE id IN ({placeholders})", tuple(vendor_ids))
            for row in cursor.fetchall():
                vendor_names[row['id']] = row['name']
        
        # Generate edit log
        from host.edit_log_generator import generate_voucher_edit_log
        try:
            edit_log = generate_voucher_edit_log(existing, new_doc, old_details, new_details, 
                                                party_names, asset_names, expense_names, vendor_names)
        except Exception as e:
            print(f"Error generating voucher edit log: {e}")
            import traceback
            traceback.print_exc()
            edit_log = f"Error generating edit log: {str(e)}"
        
        # Reverse existing ledger entries
        from host.voucher_manager import reverse_voucher_from_ledgers
        reverse_voucher_from_ledgers(voucher_no, conn)
        
        # Update voucher master (set edited_by and edit_log_history on update, never change created_by)
        cursor.execute("""
            UPDATE voucher_master
            SET voucher_date = %s, description = %s, total_amount = %s, edited_by = %s, edit_log_history = %s
            WHERE id = %s
        """, (voucher_req.voucher_date, voucher_req.description, total_debit, edited_by, edit_log, voucher_id))
        
        # Delete existing details
        cursor.execute("DELETE FROM voucher_detail WHERE voucher_id = %s", (voucher_id,))
        
        # Insert new details
        for detail in voucher_req.details:
            cursor.execute("""
                INSERT INTO voucher_detail (voucher_id, party_id, asset_id, expense_id, vendor_id, debit_amount, credit_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (voucher_id, detail.party_id, detail.asset_id, detail.expense_id, detail.vendor_id, detail.debit_amount, detail.credit_amount))
        
        # Post to ledgers
        from host.voucher_manager import post_voucher_to_ledgers
        if not post_voucher_to_ledgers(voucher_id, conn):
            conn.rollback()
            raise HTTPException(status_code=500, detail="Failed to post voucher to ledgers")
        
        conn.commit()
        cursor.close()
        
        return {"success": True, "voucher_id": voucher_id}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Update voucher error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.delete("/api/vouchers/{voucher_id}")
async def delete_voucher(voucher_id: int, request: Request):
    """Delete a voucher"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        
        # Get voucher number before deletion
        cursor.execute("SELECT voucher_no FROM voucher_master WHERE id = %s", (voucher_id,))
        voucher = cursor.fetchone()
        
        if not voucher:
            raise HTTPException(status_code=404, detail="Voucher not found")
        
        voucher_no = voucher['voucher_no']
        
        # Reverse ledger entries
        from host.voucher_manager import reverse_voucher_from_ledgers
        reverse_voucher_from_ledgers(voucher_no, conn)
        
        # Delete voucher (cascade will delete details)
        cursor.execute("DELETE FROM voucher_master WHERE id = %s", (voucher_id,))
        
        conn.commit()
        cursor.close()
        
        return {"success": True}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Delete voucher error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


# Import data entry endpoints (must be after app and all models are defined)
try:
    import host.data_entry_endpoints  # noqa: F401
except Exception as e:
    print(f"Warning: Could not import data_entry_endpoints: {e}")

# Import command endpoints (optimized write APIs)
try:
    import host.command_endpoints  # noqa: F401
except Exception as e:
    print(f"Warning: Could not import command_endpoints: {e}")

# Import snapshot and sync endpoints
try:
    import host.snapshot_endpoints  # noqa: F401
except Exception as e:
    print(f"Warning: Could not import snapshot_endpoints: {e}")

# Import batch command endpoint
try:
    import host.batch_commands  # noqa: F401
except Exception as e:
    print(f"Warning: Could not import batch_commands: {e}")

# Import invoice endpoints
try:
    import host.invoice_endpoints  # noqa: F401
except Exception as e:
    print(f"Warning: Could not import invoice_endpoints: {e}")


# ==================== WEB MODULE ROUTES ====================

MODULE_SETUP_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Module User Setup</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 400px;
            margin: 100px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .setup-container {
            background: white;
            padding: 30px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        h2 {
            margin-top: 0;
            color: #333;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 3px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 10px;
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #218838;
        }
        .error {
            color: red;
            margin-top: 10px;
            font-size: 14px;
        }
        .info {
            color: #666;
            font-size: 12px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="setup-container">
        <h2>Create Module User Account</h2>
        <p class="info">This is the first time accessing the module. Please create a module user account.</p>
        <form id="setupForm" method="POST" action="/module/setup">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <div class="form-group">
                <label for="confirm_password">Confirm Password:</label>
                <input type="password" id="confirm_password" name="confirm_password" required>
            </div>
            <button type="submit">Create Account</button>
            <div id="error" class="error"></div>
        </form>
    </div>
    <script>
        document.getElementById('setupForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const formData = new FormData(this);
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            const errorDiv = document.getElementById('error');
            const submitButton = this.querySelector('button[type="submit"]');
            
            errorDiv.textContent = '';
            
            // Validate passwords match
            if (password !== confirmPassword) {
                errorDiv.textContent = 'Passwords do not match';
                return;
            }
            
            // Validate password length
            if (password.length < 6) {
                errorDiv.textContent = 'Password must be at least 6 characters';
                return;
            }
            
            submitButton.disabled = true;
            submitButton.textContent = 'Creating...';
            
            try {
                const response = await fetch('/module/setup', {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                    },
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                
                if (data.success) {
                    window.location.href = '/module';
                } else {
                    errorDiv.textContent = data.message || 'Setup failed';
                    submitButton.disabled = false;
                    submitButton.textContent = 'Create Account';
                }
            } catch (error) {
                errorDiv.textContent = 'Connection error. Please try again.';
                submitButton.disabled = false;
                submitButton.textContent = 'Create Account';
                console.error('Setup error:', error);
            }
        });
    </script>
</body>
</html>
"""

MODULE_LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Admin Login - Module</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 400px;
            margin: 100px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .login-container {
            background: white;
            padding: 30px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        h2 {
            margin-top: 0;
            color: #333;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 3px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 10px;
            background-color: #0078d4;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #005a9e;
        }
        .error {
            color: red;
            margin-top: 10px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>Module Login</h2>
        <form id="loginForm" method="POST" action="/module/login">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Login</button>
            <div id="error" class="error"></div>
        </form>
    </div>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const formData = new FormData(this);
            const errorDiv = document.getElementById('error');
            const submitButton = this.querySelector('button[type="submit"]');
            
            errorDiv.textContent = '';
            submitButton.disabled = true;
            submitButton.textContent = 'Logging in...';
            
            try {
                const response = await fetch('/module/login', {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                    },
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                
                if (data.success) {
                    // Redirect to audit module after successful login
                    window.location.href = data.redirect || '/module/audit';
                } else {
                    errorDiv.textContent = data.message || 'Login failed';
                    submitButton.disabled = false;
                    submitButton.textContent = 'Login';
                }
            } catch (error) {
                errorDiv.textContent = 'Connection error. Please try again.';
                submitButton.disabled = false;
                submitButton.textContent = 'Login';
                console.error('Login error:', error);
            }
        });
    </script>
</body>
</html>
"""

MODULE_WELCOME_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Welcome - Module</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 100px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .welcome-container {
            background: white;
            padding: 40px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }
        h1 {
            color: #0078d4;
            margin-bottom: 20px;
        }
        .status {
            margin-top: 30px;
            padding: 15px;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 3px;
            color: #155724;
        }
        .info {
            margin-top: 20px;
            padding: 15px;
            background-color: #e7f3ff;
            border: 1px solid #b3d9ff;
            border-radius: 3px;
            color: #004085;
            text-align: left;
        }
        .info strong {
            display: block;
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
    <div class="welcome-container">
        <h1>Welcome to Module</h1>
        <div class="status">
            ✓ Database connection confirmed
        </div>
        <div class="info">
            <strong>Module Status:</strong>
            <div>Web Module: ✓ Connected</div>
            <div>Server API: ✓ Connected</div>
            <div>Database: ✓ Connected</div>
        </div>
    </div>
</body>
</html>
"""


@app.get("/login", response_class=HTMLResponse)
@app.get("/module", response_class=HTMLResponse)
async def module_login_page(request: Request):
    """Serve the module login page or setup page if no module user exists"""
    conn = None
    try:
        # Check if module user exists
        conn = db_pool.get_connection()
        if not conn:
            return HTMLResponse(
                content="<html><body><h1>Error</h1><p>Database unavailable</p></body></html>",
                status_code=503
            )
        
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE role = 'MODULE_USER'")
        module_user_exists = cursor.fetchone() is not None
        cursor.close()
        
        # If no module user exists, show setup page
        if not module_user_exists:
            # For now, return setup HTML (can be extracted later)
            return HTMLResponse(content=MODULE_SETUP_HTML, status_code=200)
        
        # Serve login page from template
        login_file = web_module_path / "templates" / "login.html"
        if login_file.exists():
            return FileResponse(str(login_file))
        else:
            # Fallback to embedded HTML
            return HTMLResponse(content=MODULE_LOGIN_HTML, status_code=200)
    except Exception as e:
        print(f"Error serving module page: {e}")
        import traceback
        traceback.print_exc()
        return HTMLResponse(
            content="<html><body><h1>Error</h1><p>Failed to load module page</p></body></html>",
            status_code=500
        )
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/module/setup")
async def module_setup(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Create module user account (first-time setup)"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        return JSONResponse(
            status_code=429,
            content={"success": False, "message": "Rate limit exceeded"}
        )
    
    # Validate inputs
    if not username or len(username.strip()) == 0:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Username is required"}
        )
    
    if not password or len(password) < 6:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Password must be at least 6 characters"}
        )
    
    if password != confirm_password:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Passwords do not match"}
        )
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            return JSONResponse(
                status_code=503,
                content={"success": False, "message": "Database unavailable"}
            )
        
        cursor = conn.cursor(dictionary=True)
        
        # Check if module user already exists
        cursor.execute("SELECT id FROM users WHERE role = 'MODULE_USER'")
        if cursor.fetchone():
            cursor.close()
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Module user already exists. Please login instead."}
            )
        
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (username.strip(),))
        if cursor.fetchone():
            cursor.close()
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Username already exists"}
            )
        
        # Hash password
        password_hash = hash_password(password)
        
        # Insert module user
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            (username.strip(), password_hash, "MODULE_USER")
        )
        conn.commit()
        cursor.close()
        
        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Module user created successfully"}
        )
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Module setup error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Server error: {str(e)}"}
        )
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/api/module/login")
@app.post("/module/login")
async def module_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Handle module admin login"""
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        return JSONResponse(
            status_code=429,
            content={"success": False, "message": "Rate limit exceeded"}
        )
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            return JSONResponse(
                status_code=503,
                content={"success": False, "message": "Database unavailable"}
            )
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, username, password_hash, role FROM users WHERE username = %s",
            (username,)
        )
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid credentials"}
            )
        
        # Check if user is MODULE_USER (only module users allowed, not admin)
        if user["role"] != "MODULE_USER":
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Access denied. Only module user credentials are allowed."}
            )
        
        if not verify_password(password, user["password_hash"]):
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid credentials"}
            )
        
        # Test database connection - if we got here, database is working
        # But let's do a simple test to confirm
        try:
            # Use a fresh cursor and ensure we consume the result
            test_cursor = conn.cursor()
            test_cursor.execute("SELECT 1 as test")
            result = test_cursor.fetchone()  # Consume the result
            test_cursor.close()
            db_connected = True
        except Exception as db_error:
            print(f"Database connection test error: {db_error}")
            import traceback
            traceback.print_exc()
            # If we got the user data, database is clearly working, so this is just a test issue
            # Don't fail the login if we successfully queried the user
            db_connected = True  # Assume connected since we got user data
        
        # Note: If we successfully queried the user, database is clearly connected
        # The test above is just for confirmation
        
        # Create session
        session_id = secrets.token_urlsafe(32)
        expires = datetime.now() + SESSION_TIMEOUT
        
        with module_sessions_lock:
            # Clean up expired sessions
            now = datetime.now()
            expired_sessions = [sid for sid, sess in module_sessions.items() if sess.get("expires", now) < now]
            for sid in expired_sessions:
                del module_sessions[sid]
            
            # Store new session
            module_sessions[session_id] = {
                "username": user["username"],
                "role": user["role"],
                "expires": expires
            }
        
        # Return success with session cookie
        response = JSONResponse(
            status_code=200,
            content={"success": True, "message": "Login successful", "redirect": "/module/audit"}
        )
        response.set_cookie(
            key="module_session",
            value=session_id,
            max_age=int(SESSION_TIMEOUT.total_seconds()),
            httponly=True,
            samesite="lax"
        )
        return response
        
    except Exception as e:
        print(f"Module login error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Server error: {str(e)}"}
        )
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/module/welcome", response_class=HTMLResponse)
async def module_welcome(request: Request):
    """Serve the module welcome page after successful login"""
    # Note: In a production system, you would verify the session/token here
    # For Phase 1 (connection test only), we'll just show the welcome page
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            return HTMLResponse(
                content="<html><body><h1>Error</h1><p>Database connection failed</p></body></html>",
                status_code=503
            )
        
        # Test database connection - ensure we consume the result
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()  # Consume the result to avoid "Unread result found" error
        cursor.close()
        
        return HTMLResponse(content=MODULE_WELCOME_HTML)
    except Exception as e:
        print(f"Module welcome page database test error: {e}")
        import traceback
        traceback.print_exc()
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>Database connection test failed: {str(e)}</p></body></html>",
            status_code=503
        )
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.post("/api/module/logout")
@app.post("/module/logout")
async def module_logout(request: Request):
    """Handle module logout"""
    session_id = request.cookies.get("module_session")
    if session_id:
        with module_sessions_lock:
            if session_id in module_sessions:
                del module_sessions[session_id]
    
    response = JSONResponse(
        status_code=200,
        content={"success": True, "message": "Logged out successfully"}
    )
    response.delete_cookie(key="module_session")
    return response


# ==================== AUDIT MODULE HTML PAGES ====================

AUDIT_MODULE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Audit Module - Form Tracking</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
        }
        .header {
            background: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .header .subtitle {
            color: #666;
            font-size: 14px;
        }
        .controls {
            background: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        .controls input, .controls select {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 3px;
            font-size: 14px;
        }
        .controls input[type="text"] {
            flex: 1;
            min-width: 200px;
        }
        .table-container {
            background: white;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        thead {
            background-color: #f8f9fa;
            position: sticky;
            top: 0;
        }
        th {
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #dee2e6;
            cursor: pointer;
            user-select: none;
        }
        th:hover {
            background-color: #e9ecef;
        }
        th.sort-asc::after {
            content: " ▲";
            font-size: 10px;
        }
        th.sort-desc::after {
            content: " ▼";
            font-size: 10px;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
        }
        tbody tr {
            cursor: pointer;
            transition: background-color 0.2s;
        }
        tbody tr:hover {
            background-color: #f8f9fa;
        }
        tbody tr.selected {
            background-color: #e7f3ff;
        }
        .form-type-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .badge-inward { background-color: #d4edda; color: #155724; }
        .badge-outward { background-color: #fff3cd; color: #856404; }
        .badge-transfer { background-color: #cfe2ff; color: #084298; }
        .badge-transfer-bn { background-color: #d1ecf1; color: #0c5460; }
        .badge-invoice { background-color: #f8d7da; color: #721c24; }
        .badge-voucher-cp { background-color: #e2e3e5; color: #383d41; }
        .badge-voucher-cr { background-color: #d1ecf1; color: #0c5460; }
        .badge-voucher-jv { background-color: #d4edda; color: #155724; }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            margin-top: 20px;
            padding: 15px;
        }
        .pagination button {
            padding: 8px 15px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 3px;
            cursor: pointer;
        }
        .pagination button:hover:not(:disabled) {
            background: #f8f9fa;
        }
        .pagination button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .pagination .page-info {
            padding: 8px 15px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>📋 Audit Module - Form Tracking</h1>
            <div class="subtitle">View, audit, and compare all forms and vouchers in the system</div>
        </div>
        <button onclick="logout()" style="padding: 10px 20px; background: #dc3545; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 14px;">Logout</button>
    </div>
    
    <div class="controls">
        <input type="text" id="searchInput" placeholder="Search by form number, party, or user...">
        <select id="formTypeFilter">
            <option value="">All Form Types</option>
            <option value="inward">Inward</option>
            <option value="outward">Outward</option>
            <option value="transfer">Transfer</option>
            <option value="transfer_bn">Transfer by Name</option>
            <option value="invoice">Invoice</option>
            <option value="voucher_cp">Voucher CP</option>
            <option value="voucher_cr">Voucher CR</option>
            <option value="voucher_jv">Voucher JV</option>
        </select>
        <button onclick="loadForms()">Refresh</button>
    </div>
    
    <div id="errorContainer"></div>
    
    <div class="table-container">
        <div id="loading" class="loading">Loading forms...</div>
        <table id="formsTable" style="display: none;">
            <thead>
                <tr>
                    <th onclick="sortTable('entry_num')">Entry #</th>
                    <th onclick="sortTable('form_type')">Form Type</th>
                    <th onclick="sortTable('form_number')">Form #</th>
                    <th onclick="sortTable('ms_party')">MS Party</th>
                    <th onclick="sortTable('created_by')">Created By</th>
                    <th onclick="sortTable('edited_by')">Edited By</th>
                    <th onclick="sortTable('document_date')">Date</th>
                </tr>
            </thead>
            <tbody id="formsTableBody">
            </tbody>
        </table>
    </div>
    
    <div class="pagination" id="pagination" style="display: none;">
        <button id="prevBtn" onclick="changePage(-1)">Previous</button>
        <span class="page-info" id="pageInfo"></span>
        <button id="nextBtn" onclick="changePage(1)">Next</button>
    </div>
    
    <script>
        let allForms = [];
        let filteredForms = [];
        let currentPage = 1;
        const itemsPerPage = 50;
        let sortColumn = 'entry_num';
        let sortDirection = 'asc';
        
        // Load forms on page load
        window.addEventListener('DOMContentLoaded', () => {
            loadForms();
            document.getElementById('searchInput').addEventListener('input', applyFilters);
            document.getElementById('formTypeFilter').addEventListener('change', applyFilters);
        });
        
        async function loadForms() {
            const loading = document.getElementById('loading');
            const table = document.getElementById('formsTable');
            const errorContainer = document.getElementById('errorContainer');
            
            loading.style.display = 'block';
            table.style.display = 'none';
            errorContainer.innerHTML = '';
            
            try {
                const response = await fetch('/module/audit/forms');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                
                if (data.success) {
                    allForms = data.forms;
                    applyFilters();
                } else {
                    throw new Error(data.message || 'Failed to load forms');
                }
            } catch (error) {
                errorContainer.innerHTML = `<div class="error">Error loading forms: ${error.message}</div>`;
                loading.style.display = 'none';
            }
        }
        
        function applyFilters() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const formTypeFilter = document.getElementById('formTypeFilter').value;
            
            filteredForms = allForms.filter(form => {
                const matchesSearch = !searchTerm || 
                    form.form_number.toLowerCase().includes(searchTerm) ||
                    form.ms_party.toLowerCase().includes(searchTerm) ||
                    form.created_by.toLowerCase().includes(searchTerm) ||
                    form.edited_by.toLowerCase().includes(searchTerm);
                
                const matchesType = !formTypeFilter || form.form_type === formTypeFilter;
                
                return matchesSearch && matchesType;
            });
            
            currentPage = 1;
            renderTable();
        }
        
        function sortTable(column) {
            if (sortColumn === column) {
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                sortColumn = column;
                sortDirection = 'asc';
            }
            
            filteredForms.sort((a, b) => {
                let aVal = a[column] || '';
                let bVal = b[column] || '';
                
                if (column === 'entry_num') {
                    aVal = parseInt(aVal) || 0;
                    bVal = parseInt(bVal) || 0;
                }
                
                if (typeof aVal === 'string') {
                    aVal = aVal.toLowerCase();
                    bVal = bVal.toLowerCase();
                }
                
                if (sortDirection === 'asc') {
                    return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
                } else {
                    return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
                }
            });
            
            renderTable();
        }
        
        function renderTable() {
            const tbody = document.getElementById('formsTableBody');
            const table = document.getElementById('formsTable');
            const loading = document.getElementById('loading');
            const pagination = document.getElementById('pagination');
            
            const startIndex = (currentPage - 1) * itemsPerPage;
            const endIndex = startIndex + itemsPerPage;
            const pageForms = filteredForms.slice(startIndex, endIndex);
            
            tbody.innerHTML = '';
            
            pageForms.forEach(form => {
                const row = document.createElement('tr');
                row.onclick = () => viewFormDetail(form.form_type, form.form_id);
                
                const badgeClass = `badge-${form.form_type.replace('_', '-')}`;
                const formTypeLabel = form.form_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
                
                row.innerHTML = `
                    <td>${form.entry_num}</td>
                    <td><span class="form-type-badge ${badgeClass}">${formTypeLabel}</span></td>
                    <td>${form.form_number}</td>
                    <td>${form.ms_party || '-'}</td>
                    <td>${form.created_by || '-'}</td>
                    <td>${form.edited_by || '-'}</td>
                    <td>${form.document_date ? form.document_date.split('T')[0] : '-'}</td>
                `;
                tbody.appendChild(row);
            });
            
            loading.style.display = 'none';
            table.style.display = 'table';
            
            // Update pagination
            const totalPages = Math.ceil(filteredForms.length / itemsPerPage);
            if (totalPages > 1) {
                pagination.style.display = 'flex';
                document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages} (${filteredForms.length} total)`;
                document.getElementById('prevBtn').disabled = currentPage === 1;
                document.getElementById('nextBtn').disabled = currentPage === totalPages;
            } else {
                pagination.style.display = 'none';
            }
            
            // Update sort indicators
            document.querySelectorAll('th').forEach(th => {
                th.classList.remove('sort-asc', 'sort-desc');
            });
            const headerCells = document.querySelectorAll('th');
            const columnIndex = ['entry_num', 'form_type', 'form_number', 'ms_party', 'created_by', 'edited_by', 'document_date'].indexOf(sortColumn);
            if (columnIndex >= 0 && headerCells[columnIndex]) {
                headerCells[columnIndex].classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
            }
        }
        
        function changePage(direction) {
            const totalPages = Math.ceil(filteredForms.length / itemsPerPage);
            const newPage = currentPage + direction;
            if (newPage >= 1 && newPage <= totalPages) {
                currentPage = newPage;
                renderTable();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        }
        
        function viewFormDetail(formType, formId) {
            window.location.href = `/module/audit/view/${formType}/${formId}`;
        }
        
        async function logout() {
            try {
                const response = await fetch('/module/logout', {
                    method: 'POST',
                    credentials: 'include'
                });
                if (response.ok) {
                    window.location.href = '/module';
                }
            } catch (error) {
                console.error('Logout error:', error);
                // Force redirect even if logout fails
                window.location.href = '/module';
            }
        }
    </script>
</body>
</html>
"""


# ==================== AUDIT MODULE ENDPOINTS ====================

@app.get("/api/module/audit/forms")
@app.get("/module/audit/forms")
async def get_audit_forms(request: Request):
    """Get unified list of all forms for audit module"""
    session = check_module_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        all_forms = []
        entry_num = 1
        
        # Fetch Inward documents
        cursor.execute("""
            SELECT id, inward_number as form_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   created_by, edited_by, document_date, created_at
            FROM inward_documents
            ORDER BY document_date DESC, inward_number DESC
        """)
        for row in cursor.fetchall():
            all_forms.append({
                "entry_num": entry_num,
                "form_type": "inward",
                "form_id": row['id'],
                "form_number": row['form_number'],
                "ms_party": row['ms_party_name'] or '',
                "created_by": row['created_by'] or '',
                "edited_by": row['edited_by'] or '',
                "document_date": row['document_date'].isoformat() if row['document_date'] else '',
                "created_at": row['created_at'].isoformat() if row['created_at'] else ''
            })
            entry_num += 1
        
        # Fetch Outward documents
        cursor.execute("""
            SELECT id, outward_number as form_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   created_by, edited_by, document_date, created_at
            FROM outward_documents
            ORDER BY document_date DESC, outward_number DESC
        """)
        for row in cursor.fetchall():
            all_forms.append({
                "entry_num": entry_num,
                "form_type": "outward",
                "form_id": row['id'],
                "form_number": row['form_number'],
                "ms_party": row['ms_party_name'] or '',
                "created_by": row['created_by'] or '',
                "edited_by": row['edited_by'] or '',
                "document_date": row['document_date'].isoformat() if row['document_date'] else '',
                "created_at": row['created_at'].isoformat() if row['created_at'] else ''
            })
            entry_num += 1
        
        # Fetch Transfer documents (simple)
        cursor.execute("""
            SELECT id, transfer_number as form_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   created_by, edited_by, document_date, created_at
            FROM transfer_documents
            WHERE transfer_type = 'simple'
            ORDER BY document_date DESC, transfer_number DESC
        """)
        for row in cursor.fetchall():
            all_forms.append({
                "entry_num": entry_num,
                "form_type": "transfer",
                "form_id": row['id'],
                "form_number": row['form_number'],
                "ms_party": row['ms_party_name'] or '',
                "created_by": row['created_by'] or '',
                "edited_by": row['edited_by'] or '',
                "document_date": row['document_date'].isoformat() if row['document_date'] else '',
                "created_at": row['created_at'].isoformat() if row['created_at'] else ''
            })
            entry_num += 1
        
        # Fetch Transfer by Name documents
        cursor.execute("""
            SELECT id, transfer_number as form_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   created_by, edited_by, document_date, created_at
            FROM transfer_documents
            WHERE transfer_type = 'by_name'
            ORDER BY document_date DESC, transfer_number DESC
        """)
        for row in cursor.fetchall():
            all_forms.append({
                "entry_num": entry_num,
                "form_type": "transfer_bn",
                "form_id": row['id'],
                "form_number": row['form_number'],
                "ms_party": row['ms_party_name'] or '',
                "created_by": row['created_by'] or '',
                "edited_by": row['edited_by'] or '',
                "document_date": row['document_date'].isoformat() if row['document_date'] else '',
                "created_at": row['created_at'].isoformat() if row['created_at'] else ''
            })
            entry_num += 1
        
        # Fetch Invoices
        cursor.execute("""
            SELECT id, invoice_number as form_number, ms_party_id,
                   (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                   created_by, edited_by, invoice_date as document_date, created_at
            FROM invoices
            ORDER BY invoice_date DESC, invoice_number DESC
        """)
        for row in cursor.fetchall():
            all_forms.append({
                "entry_num": entry_num,
                "form_type": "invoice",
                "form_id": row['id'],
                "form_number": row['form_number'],
                "ms_party": row['ms_party_name'] or '',
                "created_by": row['created_by'] or '',
                "edited_by": row['edited_by'] or '',
                "document_date": row['document_date'].isoformat() if row['document_date'] else '',
                "created_at": row['created_at'].isoformat() if row['created_at'] else ''
            })
            entry_num += 1
        
        # Fetch Vouchers (CP, CR, JV)
        cursor.execute("""
            SELECT vm.id, vm.voucher_no as form_number, vm.voucher_type,
                   vm.created_by, vm.edited_by, vm.voucher_date as document_date, vm.created_at,
                   (SELECT l.name FROM voucher_detail vd 
                    JOIN liabilities l ON vd.party_id = l.id 
                    WHERE vd.voucher_id = vm.id AND vd.party_id IS NOT NULL 
                    LIMIT 1) as ms_party_name
            FROM voucher_master vm
            ORDER BY vm.voucher_date DESC, vm.voucher_no DESC
        """)
        for row in cursor.fetchall():
            form_type_map = {'CP': 'voucher_cp', 'CR': 'voucher_cr', 'JV': 'voucher_jv'}
            all_forms.append({
                "entry_num": entry_num,
                "form_type": form_type_map.get(row['voucher_type'], 'voucher'),
                "form_id": row['id'],
                "form_number": row['form_number'],
                "ms_party": row['ms_party_name'] or '',
                "created_by": row['created_by'] or '',
                "edited_by": row['edited_by'] or '',
                "document_date": row['document_date'].isoformat() if row['document_date'] else '',
                "created_at": row['created_at'].isoformat() if row['created_at'] else ''
            })
            entry_num += 1
        
        cursor.close()
        return {"success": True, "forms": all_forms}
    except Exception as e:
        print(f"Get audit forms error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


@app.get("/api/module/audit/form/{form_type}/{form_id}")
@app.get("/module/audit/form/{form_type}/{form_id}")
async def get_audit_form_detail(form_type: str, form_id: int, request: Request):
    """Get detailed form data for audit module"""
    session = check_module_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    client_ip = get_client_ip(request)
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    conn = None
    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        cursor = conn.cursor(dictionary=True)
        form_data = None
        
        if form_type == "inward":
            cursor.execute("""
                SELECT id, inward_number, gp_number, sr_number, ms_party_id,
                       (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                       from_party, vehicle_number, driver_name, total_quantity,
                       document_date, created_by, edited_by, edit_log_history, created_at
                FROM inward_documents
                WHERE id = %s
            """, (form_id,))
            doc = cursor.fetchone()
            if doc:
                cursor.execute("""
                    SELECT item_name, measurement, quantity
                    FROM inward_items
                    WHERE inward_document_id = %s
                    ORDER BY item_name, measurement
                """, (form_id,))
                items = cursor.fetchall()
                for item in items:
                    item['quantity'] = float(item['quantity'])
                doc['items'] = items
                doc['total_quantity'] = float(doc['total_quantity'])
                form_data = doc
        
        elif form_type == "outward":
            cursor.execute("""
                SELECT id, outward_number, gp_number, sr_number, ms_party_id,
                       (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                       from_party, outward_to, vehicle_number, driver_name, total_quantity,
                       document_date, created_by, edited_by, edit_log_history, created_at
                FROM outward_documents
                WHERE id = %s
            """, (form_id,))
            doc = cursor.fetchone()
            if doc:
                cursor.execute("""
                    SELECT item_name, measurement, quantity
                    FROM outward_items
                    WHERE outward_document_id = %s
                    ORDER BY item_name, measurement
                """, (form_id,))
                items = cursor.fetchall()
                for item in items:
                    item['quantity'] = float(item['quantity'])
                doc['items'] = items
                doc['total_quantity'] = float(doc['total_quantity'])
                form_data = doc
        
        elif form_type == "transfer":
            cursor.execute("""
                SELECT id, transfer_number, gp_number, sr_number, ms_party_id,
                       (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                       from_party, transfer_to, transfer_to_ms_party_id,
                       (SELECT name FROM liabilities WHERE id = transfer_to_ms_party_id) as transfer_to_ms_party_name,
                       vehicle_number, driver_name, total_quantity, transfer_type,
                       document_date, created_by, edited_by, edit_log_history, created_at
                FROM transfer_documents
                WHERE id = %s AND transfer_type = 'simple'
            """, (form_id,))
            doc = cursor.fetchone()
            if doc:
                cursor.execute("""
                    SELECT item_name, measurement, quantity
                    FROM transfer_items
                    WHERE transfer_document_id = %s
                    ORDER BY item_name, measurement
                """, (form_id,))
                items = cursor.fetchall()
                for item in items:
                    item['quantity'] = float(item['quantity'])
                doc['items'] = items
                doc['total_quantity'] = float(doc['total_quantity'])
                form_data = doc
        
        elif form_type == "transfer_bn":
            cursor.execute("""
                SELECT id, transfer_number, gp_number, sr_number, ms_party_id,
                       (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                       from_party, transfer_to, transfer_to_ms_party_id,
                       (SELECT name FROM liabilities WHERE id = transfer_to_ms_party_id) as transfer_to_ms_party_name,
                       vehicle_number, driver_name, total_quantity, transfer_type,
                       document_date, created_by, edited_by, edit_log_history, created_at
                FROM transfer_documents
                WHERE id = %s AND transfer_type = 'by_name'
            """, (form_id,))
            doc = cursor.fetchone()
            if doc:
                cursor.execute("""
                    SELECT item_name, measurement, quantity
                    FROM transfer_items
                    WHERE transfer_document_id = %s
                    ORDER BY item_name, measurement
                """, (form_id,))
                items = cursor.fetchall()
                for item in items:
                    item['quantity'] = float(item['quantity'])
                doc['items'] = items
                doc['total_quantity'] = float(doc['total_quantity'])
                form_data = doc
        
        elif form_type == "invoice":
            cursor.execute("""
                SELECT id, invoice_number, ms_party_id,
                       (SELECT name FROM liabilities WHERE id = ms_party_id) as ms_party_name,
                       number_of_items, discount_amount, discount_source, total_amount,
                       invoice_date, created_by, edited_by, edit_log_history, created_at
                FROM invoices
                WHERE id = %s
            """, (form_id,))
            doc = cursor.fetchone()
            if doc:
                cursor.execute("""
                    SELECT ii.id, ii.item_name, ii.measurement, ii.quantity, ii.rate, ii.amount,
                           od.outward_number, td.transfer_number
                    FROM invoice_items ii
                    LEFT JOIN outward_documents od ON ii.outward_document_id = od.id
                    LEFT JOIN transfer_documents td ON ii.transfer_document_id = td.id
                    WHERE ii.invoice_id = %s
                    ORDER BY ii.id
                """, (form_id,))
                items = cursor.fetchall()
                for item in items:
                    item['quantity'] = float(item['quantity'])
                    item['rate'] = float(item['rate']) if item['rate'] else 0
                    item['amount'] = float(item['amount']) if item['amount'] else 0
                doc['items'] = items
                doc['total_amount'] = float(doc['total_amount'])
                doc['discount_amount'] = float(doc['discount_amount'])
                form_data = doc
        
        elif form_type in ["voucher_cp", "voucher_cr", "voucher_jv"]:
            voucher_type_map = {'voucher_cp': 'CP', 'voucher_cr': 'CR', 'voucher_jv': 'JV'}
            voucher_type = voucher_type_map.get(form_type, 'JV')
            cursor.execute("""
                SELECT id, voucher_no, voucher_type, voucher_date, description, total_amount,
                       created_by, edited_by, edit_log_history, created_at, updated_at
                FROM voucher_master
                WHERE id = %s AND voucher_type = %s
            """, (form_id, voucher_type))
            doc = cursor.fetchone()
            if doc:
                cursor.execute("""
                    SELECT vd.id, vd.party_id, vd.asset_id, vd.expense_id, vd.vendor_id, 
                           vd.debit_amount, vd.credit_amount,
                           l.name as party_name,
                           a.name as asset_name,
                           e.name as expense_name,
                           v.name as vendor_name
                    FROM voucher_detail vd
                    LEFT JOIN liabilities l ON vd.party_id = l.id
                    LEFT JOIN assets a ON vd.asset_id = a.id
                    LEFT JOIN expenses e ON vd.expense_id = e.id
                    LEFT JOIN vendors v ON vd.vendor_id = v.id
                    WHERE vd.voucher_id = %s
                    ORDER BY vd.id ASC
                """, (form_id,))
                details = cursor.fetchall()
                for detail in details:
                    detail['debit_amount'] = float(detail['debit_amount']) if detail['debit_amount'] else None
                    detail['credit_amount'] = float(detail['credit_amount']) if detail['credit_amount'] else None
                doc['details'] = details
                doc['total_amount'] = float(doc['total_amount'])
                form_data = doc
        
        cursor.close()
        
        if not form_data:
            raise HTTPException(status_code=404, detail="Form not found")
        
        # Convert dates
        for date_field in ['document_date', 'invoice_date', 'voucher_date', 'created_at', 'updated_at']:
            if date_field in form_data and form_data[date_field]:
                if hasattr(form_data[date_field], 'isoformat'):
                    form_data[date_field] = form_data[date_field].isoformat()
                else:
                    form_data[date_field] = str(form_data[date_field])
        
        return {"success": True, "form": form_data, "form_type": form_type}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get audit form detail error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            db_pool.return_connection(conn)


def check_module_session(request: Request) -> Optional[Dict]:
    """Check if user has valid module session"""
    session_id = request.cookies.get("module_session")
    if not session_id:
        return None
    
    with module_sessions_lock:
        session = module_sessions.get(session_id)
        if not session:
            return None
        
        # Check if session expired
        if session.get("expires", datetime.now()) < datetime.now():
            del module_sessions[session_id]
            return None
        
        return session
    
    return None


@app.get("/audit", response_class=HTMLResponse)
@app.get("/module/audit", response_class=HTMLResponse)
async def audit_module_page(request: Request):
    """Serve the audit module main page - requires module authentication"""
    session = check_module_session(request)
    if not session:
        # Redirect to login if not authenticated
        return RedirectResponse(url="/login", status_code=302)
    
    # Serve audit page from template
    audit_file = web_module_path / "templates" / "audit.html"
    if audit_file.exists():
        return FileResponse(str(audit_file))
    else:
        # Fallback to embedded HTML
        return HTMLResponse(content=AUDIT_MODULE_HTML, status_code=200)


@app.get("/audit/view/{form_type}/{form_id}", response_class=HTMLResponse)
@app.get("/module/audit/view/{form_type}/{form_id}", response_class=HTMLResponse)
async def audit_form_detail_page(form_type: str, form_id: int, request: Request):
    """Serve the audit form detail page - requires module authentication"""
    session = check_module_session(request)
    if not session:
        # Redirect to login if not authenticated
        return RedirectResponse(url="/login", status_code=302)
    
    # Serve detail page from template
    detail_file = web_module_path / "templates" / "detail.html"
    if detail_file.exists():
        return FileResponse(str(detail_file))
    else:
        # Fallback - return simple error page
        return HTMLResponse(
            content="<html><body><h1>Error</h1><p>Detail template not found</p></body></html>",
            status_code=500
        )


def start_api_server():
    """Start the API server in a separate thread"""
    import uvicorn
    import asyncio
    import socket
    
    try:
        # Check if port is already in use (check localhost, not 0.0.0.0)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", API_PORT))
        sock.close()
        
        if result == 0:
            print(f"[WARN] Port {API_PORT} is already in use. Server may already be running.")
            return
        
        print(f"API Server starting on http://{API_HOST}:{API_PORT}...")
        print(f"Server listening on all interfaces (0.0.0.0) - accessible via localhost and ZeroTier")
        
        # Create new event loop for this thread (required for threading)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Configure uvicorn server
        config = uvicorn.Config(
            app,
            host=API_HOST,
            port=API_PORT,
            log_level="info",
            access_log=False,
            loop="asyncio"
        )
        server = uvicorn.Server(config)
        
        # Run server in the event loop (this blocks until server stops)
        print(f"API Server running on http://{API_HOST}:{API_PORT}")
        print(f"Server is accessible via:")
        print(f"  - localhost: http://127.0.0.1:{API_PORT}")
        print(f"  - ZeroTier: http://<zerotier-ip>:{API_PORT}")
        loop.run_until_complete(server.serve())
        
    except OSError as e:
        error_str = str(e)
        if any(x in error_str for x in ["Address already in use", "Only one usage", "WinError 10048", "10048"]):
            print(f"[WARN] Port {API_PORT} is already in use. Another instance may be running.")
        else:
            print(f"API Server OS error: {e}")
            import traceback
            traceback.print_exc()
    except Exception as e:
        print(f"API Server error: {e}")
        import traceback
        traceback.print_exc()
        # Try to write error to file for debugging
        try:
            error_log = Path(os.getenv("LOCALAPPDATA", ".")) / "TMS" / "api_server_error.log"
            error_log.parent.mkdir(parents=True, exist_ok=True)
            with open(error_log, "w") as f:
                f.write(f"API Server Error: {e}\n")
                traceback.print_exc(file=f)
        except:
            pass

