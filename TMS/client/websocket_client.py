"""WebSocket Client for TMS Client Application"""

import asyncio
import json
import threading
import time
from typing import Optional, Callable, Dict, Any
from websockets.client import connect
from websockets.exceptions import ConnectionClosed, InvalidURI
import sys
from common.config import CLIENT_PRIMARY_SERVER, CLIENT_FALLBACK_SERVER
from client.config_loader import load_client_config, get_server_url


class WebSocketClient:
    """WebSocket client for real-time communication with TMS server"""
    
    def __init__(self, on_message: Optional[Callable[[Dict], None]] = None):
        """
        Initialize WebSocket client
        
        Args:
            on_message: Callback function to handle incoming messages
        """
        self.on_message = on_message
        self.websocket = None
        self.connected = False
        self.running = False
        self.loop = None
        self.thread = None
        self.server_url = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        
        # Load client config from JSON file
        self.client_config = load_client_config()
        
    def _is_host_mode(self) -> bool:
        """Detect if running as host application"""
        if hasattr(sys, 'executable') and sys.executable:
            exe_name = sys.executable.lower()
            if 'host' in exe_name or 'tms-host' in exe_name:
                return True
        return False
    
    def _get_websocket_url(self, base_url: str) -> str:
        """Convert HTTP/HTTPS URL to WebSocket URL"""
        if base_url.startswith("https://"):
            return base_url.replace("https://", "wss://")
        elif base_url.startswith("http://"):
            return base_url.replace("http://", "ws://")
        else:
            # Assume it's already a WebSocket URL or add ws://
            if not base_url.startswith(("ws://", "wss://")):
                return f"ws://{base_url}"
            return base_url
    
    def _run_websocket_loop(self):
        """Run WebSocket event loop in a separate thread"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect_and_listen())
    
    async def _connect_and_listen(self):
        """Connect to WebSocket server and listen for messages"""
        is_host = self._is_host_mode()
        
        # Determine which server to connect to
        if is_host:
            # Host mode: only try localhost
            servers = [CLIENT_FALLBACK_SERVER]
        else:
            # Client mode: ONLY use ZeroTier IP from config (no fallback)
            if self.client_config:
                zerotier_server = get_server_url(self.client_config)
                servers = [zerotier_server]  # Only ZeroTier, no fallback
            else:
                # Config required - cannot connect without it
                print("[WebSocket] ERROR: client_config.json not found! Cannot connect.")
                servers = []
        
        while self.running:
            for base_url in servers:
                try:
                    ws_url = f"{self._get_websocket_url(base_url)}/ws"
                    self.server_url = ws_url
                    
                    print(f"Connecting to WebSocket: {ws_url}")
                    async with connect(ws_url, ping_interval=20, ping_timeout=10) as websocket:
                        self.websocket = websocket
                        self.connected = True
                        self.reconnect_attempts = 0
                        print(f"WebSocket connected to {base_url}")
                        
                        # Send initial subscription
                        await websocket.send(json.dumps({
                            "type": "subscribe",
                            "channels": ["updates", "notifications"]
                        }))
                        
                        # Listen for messages
                        async for message in websocket:
                            if not self.running:
                                break
                                
                            try:
                                data = json.loads(message)
                                if self.on_message:
                                    # NOTE: This callback is invoked from the WS thread.
                                    # For PyQt UIs, pass a callback that emits a Qt signal (thread-safe).
                                    self.on_message(data)
                            except json.JSONDecodeError:
                                print(f"Invalid JSON received: {message}")
                            except Exception as e:
                                print(f"Error processing WebSocket message: {e}")
                        
                        # Connection closed
                        self.connected = False
                        print("WebSocket connection closed")
                        
                        # If we were connected and it closed, try to reconnect
                        if self.running and self.reconnect_attempts < self.max_reconnect_attempts:
                            self.reconnect_attempts += 1
                            print(f"Attempting to reconnect... ({self.reconnect_attempts}/{self.max_reconnect_attempts})")
                            await asyncio.sleep(self.reconnect_delay)
                            break  # Break to try next server or retry
                        else:
                            if self.reconnect_attempts >= self.max_reconnect_attempts:
                                print("Max reconnection attempts reached")
                                self.running = False
                                return
                            
                except (ConnectionClosed, InvalidURI, OSError, Exception) as e:
                    print(f"WebSocket connection error to {base_url}: {e}")
                    self.connected = False
                    
                    # If this was the last server, wait before retrying
                    if base_url == servers[-1]:
                        if self.reconnect_attempts < self.max_reconnect_attempts:
                            self.reconnect_attempts += 1
                            print(f"All servers failed. Retrying in {self.reconnect_delay}s... ({self.reconnect_attempts}/{self.max_reconnect_attempts})")
                            await asyncio.sleep(self.reconnect_delay)
                        else:
                            print("Max reconnection attempts reached")
                            self.running = False
                            return
                    continue
            
            if not self.running:
                break
    
    def start(self):
        """Start WebSocket client in background thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_websocket_loop, daemon=True, name="WebSocketClient")
        self.thread.start()
        print("WebSocket client started")
    
    def stop(self):
        """Stop WebSocket client"""
        self.running = False
        self.connected = False
        
        if self.loop and self.loop.is_running():
            # Schedule close in the event loop
            asyncio.run_coroutine_threadsafe(self._close_connection(), self.loop)
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        
        print("WebSocket client stopped")
    
    async def _close_connection(self):
        """Close WebSocket connection"""
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass
    
    def send_message(self, message: Dict[str, Any]):
        """Send a message through WebSocket (thread-safe)"""
        if not self.connected or not self.websocket or not self.loop:
            return False
        
        try:
            asyncio.run_coroutine_threadsafe(
                self._send_async(json.dumps(message)),
                self.loop
            )
            return True
        except Exception as e:
            print(f"Error sending WebSocket message: {e}")
            return False
    
    async def _send_async(self, message: str):
        """Send message asynchronously"""
        if self.websocket:
            await self.websocket.send(message)
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.connected and self.websocket is not None

