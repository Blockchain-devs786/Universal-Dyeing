"""API Client for TMS Client Application"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict
import sys
import time
from common.config import CLIENT_PRIMARY_SERVER, CLIENT_FALLBACK_SERVER
from client.config_loader import load_client_config, get_server_url


def _is_host_mode():
    """Detect if running as host application"""
    # Check if executable name contains 'host' (case insensitive) - most reliable
    if hasattr(sys, 'executable') and sys.executable:
        exe_name = sys.executable.lower()
        if 'host' in exe_name or 'tms-host' in exe_name:
            return True
    
    # Check if main module is from host package
    if hasattr(sys, 'argv') and sys.argv:
        main_script = sys.argv[0].lower()
        if 'host' in main_script and 'main' in main_script:
            return True
    
    # Check if host.main is in sys.modules (host application started)
    if 'host.main' in sys.modules:
        return True
    
    # Check if we're running from host directory by checking __main__
    try:
        import __main__
        if hasattr(__main__, '__file__'):
            main_file = __main__.__file__.lower()
            if 'host' in main_file and 'main.py' in main_file:
                return True
    except:
        pass
    
    # Default to client mode
    return False


class APIClient:
    """Client for communicating with TMS API server with automatic fallback and connection pooling"""
    
    def __init__(self, username: Optional[str] = None, mode: Optional[str] = None):
        """
        Initialize API client
        
        Args:
            username: Optional username for API requests
            mode: 'client' (only remote), 'host' (only localhost), or None (auto-detect)
        """
        # Load client config from JSON file
        self.client_config = load_client_config()
        
        # Determine server URLs based on config
        if self.client_config:
            # Use ZeroTier IP from config (ONLY ZeroTier, no fallback)
            zerotier_server = get_server_url(self.client_config)
            self.primary_server = zerotier_server
            self.fallback_server = None  # No fallback - only ZeroTier
            # Use timeout from config
            self.timeout = self.client_config.get("timeout", 5)
        else:
            # If config not available, show error (config is required)
            print("[ERROR] client_config.json not found! ZeroTier configuration required.")
            self.primary_server = None
            self.fallback_server = None
            self.timeout = 5
        
        self.current_server = None
        self.localhost_timeout = 1  # Very fast timeout for localhost check
        self.username = username
        self.server_preference = None  # Cache which server works
        
        # Auto-detect mode if not specified
        if mode is None:
            self.is_host_mode = _is_host_mode()
        else:
            self.is_host_mode = (mode == 'host')
        
        # Create session with connection pooling
        self.session = requests.Session()
        
        # Configure retry strategy - reduced retries for faster failure detection
        retry_strategy = Retry(
            total=1,  # Reduced from 2 to 1 for faster failure
            backoff_factor=0.1,  # Reduced backoff
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
            connect=0,  # No retries on connection errors - fail fast
            read=0,  # No retries on read errors - fail fast
            redirect=0  # No retries on redirects
        )
        
        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=10,  # Number of connection pools to cache
            pool_maxsize=20,      # Maximum number of connections to save in the pool
            max_retries=retry_strategy,
            pool_block=False
        )
        
        # Mount adapter for both HTTP and HTTPS
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def set_username(self, username: str):
        """Set the username for API requests"""
        self.username = username
    
    def _try_request(self, method: str, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Optional[requests.Response]:
        """
        Try request based on mode:
        - Host mode: Only try localhost
        - Client mode: Try remote server FIRST (fast), then quick localhost check if needed
        """
        # Add username header if available
        headers = kwargs.get('headers', {})
        if self.username:
            headers['X-Username'] = self.username
        kwargs['headers'] = headers
        
        # Add params if provided
        if params:
            kwargs['params'] = params
        
        if self.is_host_mode:
            # HOST MODE: Only connect to localhost
            if not self.fallback_server:
                self.fallback_server = CLIENT_FALLBACK_SERVER
            try:
                url = f"{self.fallback_server}{endpoint}"
                print(f"[APIClient] HOST MODE: Trying {url} with timeout={self.timeout}s")
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                print(f"[APIClient] HOST MODE: Response status={response.status_code}")
                # Accept 2xx status codes (200, 201, etc.)
                if 200 <= response.status_code < 300:
                    self.current_server = self.fallback_server
                    return response
                # For error responses (4xx, 5xx), still return the response so caller can handle it
                elif response.status_code >= 400:
                    self.current_server = self.fallback_server
                    return response
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ConnectTimeout) as e:
                # Connection errors - server offline
                print(f"[APIClient] HOST MODE: Connection error - {type(e).__name__}: {str(e)}")
                pass
            except Exception as e:
                # Other errors
                print(f"[APIClient] HOST MODE: Other error - {type(e).__name__}: {str(e)}")
                pass
        else:
            # CLIENT MODE: Only connect to ZeroTier IP (no remote server, no localhost fallback)
            if not self.primary_server:
                print("[APIClient] CLIENT MODE: No server configured! Check client_config.json")
                return None
            
            # Only try ZeroTier server
            try:
                url = f"{self.primary_server}{endpoint}"
                print(f"[APIClient] CLIENT MODE: Connecting to ZeroTier server {url} with timeout={self.timeout}s")
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                print(f"[APIClient] CLIENT MODE: Response status={response.status_code}")
                # Accept 2xx status codes (200, 201, etc.)
                if 200 <= response.status_code < 300:
                    self.current_server = self.primary_server
                    return response
                # For error responses (4xx, 5xx), still return the response so caller can handle it
                elif response.status_code >= 400:
                    self.current_server = self.primary_server
                    return response
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ConnectTimeout) as e:
                # Connection failed
                print(f"[APIClient] CLIENT MODE: Connection failed - {type(e).__name__}: {str(e)}")
                print(f"[APIClient] CLIENT MODE: Check ZeroTier connection and server status")
                pass
            except Exception as e:
                # Other errors
                print(f"[APIClient] CLIENT MODE: Error - {type(e).__name__}: {str(e)}")
                pass
        
        self.current_server = None
        print(f"[APIClient] All connection attempts failed for {endpoint}")
        return None
    
    def _try_request_with_retry(self, method: str, endpoint: str, max_retries: int = 5, params: Optional[Dict] = None, **kwargs) -> Optional[requests.Response]:
        """
        Wrapper around _try_request that retries on connection failure.
        
        Retries up to max_retries times with exponential back-off on connection
        failures (when _try_request returns None). Does NOT retry on server errors
        (4xx/5xx) since those indicate the server received the request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            max_retries: Maximum number of retry attempts (default 5)
            params: Optional query parameters
            **kwargs: Additional arguments passed to _try_request
        """
        for attempt in range(max_retries + 1):
            response = self._try_request(method, endpoint, params=params, **kwargs)
            
            if response is not None:
                # Got a response (success or server error) - don't retry
                return response
            
            # Connection failed - retry with back-off
            if attempt < max_retries:
                wait_time = 0.5 * (2 ** attempt)  # 0.5, 1, 2, 4, 8 seconds
                print(f"[APIClient] Connection failed for {endpoint}. Retry {attempt + 1}/{max_retries} in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"[APIClient] All {max_retries + 1} attempts failed for {endpoint}. Giving up.")
        
        return None
    
    def get_parties(self) -> Optional[Dict]:
        """Get all liabilities (via existing parties API)"""
        response = self._try_request("GET", "/api/parties")
        if response:
            return response.json()
        return None
    
    def get_all_parties(self) -> Optional[Dict]:
        """Get all unique liability/party names (from Party Management)"""
        response = self._try_request("GET", "/api/all-parties")
        if response:
            return response.json()
        return None
    
    def get_party_changelog(self, party_id: int) -> Optional[Dict]:
        """Get changelog for a liability (party backend)"""
        response = self._try_request("GET", f"/api/parties/{party_id}/changelog")
        if response:
            return response.json()
        return None
    
    def create_party(self, name: str, rate_15_yards: float, rate_22_yards: float, discount_percent: float) -> Optional[Dict]:
        """Create a new liability (via parties API)"""
        response = self._try_request_with_retry(
            "POST",
            "/api/parties",
            json={
                "name": name,
                "rate_15_yards": rate_15_yards,
                "rate_22_yards": rate_22_yards,
                "discount_percent": discount_percent
            }
        )
        if response:
            try:
                return response.json()
            except Exception:
                # If response is not JSON, return error dict
                return {"success": False, "message": f"Server error: {response.status_code}"}
        return None
    
    def update_party(self, party_id: int, name: str, rate_15_yards: float, rate_22_yards: float, discount_percent: float) -> Optional[Dict]:
        """Update an existing liability (via parties API)"""
        response = self._try_request_with_retry(
            "PUT",
            "/api/parties",
            json={
                "party_id": party_id,
                "name": name,
                "rate_15_yards": rate_15_yards,
                "rate_22_yards": rate_22_yards,
                "discount_percent": discount_percent
            }
        )
        if response:
            return response.json()
        return None
    
    def delete_party(self, party_id: int) -> Optional[Dict]:
        """Delete a liability (via parties API)"""
        response = self._try_request_with_retry("DELETE", f"/api/parties/{party_id}")
        if response:
            return response.json()
        return None

    # ---------- Name-only master modules: Assets, Expenses, Vendors ----------

    def _get_simple_master(self, endpoint: str) -> Optional[Dict]:
        """Helper to GET simple name-only masters."""
        response = self._try_request("GET", endpoint)
        if response:
            return response.json()
        return None

    def _post_simple_master(self, endpoint: str, payload: Dict) -> Optional[Dict]:
        """Helper to POST simple name-only masters."""
        response = self._try_request_with_retry("POST", endpoint, json=payload)
        if response:
            try:
                return response.json()
            except Exception:
                return {"success": False, "message": f"Server error: {response.status_code}"}
        return None

    def _put_simple_master(self, endpoint: str, payload: Dict) -> Optional[Dict]:
        """Helper to PUT simple name-only masters."""
        response = self._try_request_with_retry("PUT", endpoint, json=payload)
        if response:
            try:
                return response.json()
            except Exception:
                return {"success": False, "message": f"Server error: {response.status_code}"}
        return None

    # Assets

    def get_assets(self) -> Optional[Dict]:
        """Get all Assets master names."""
        return self._get_simple_master("/api/assets")

    def create_asset(self, name: str) -> Optional[Dict]:
        """Create a new Asset name (no financial data)."""
        return self._post_simple_master("/api/assets", {"name": name})

    def update_asset(self, asset_id: int, name: str) -> Optional[Dict]:
        """Update an existing Asset name."""
        return self._put_simple_master("/api/assets", {"id": asset_id, "name": name})

    def deactivate_asset(self, asset_id: int) -> Optional[Dict]:
        """Deactivate an Asset name (no delete)."""
        return self._put_simple_master("/api/assets/deactivate", {"id": asset_id})

    # Expenses

    def get_expenses(self) -> Optional[Dict]:
        """Get all Expenses master names."""
        return self._get_simple_master("/api/expenses")

    def create_expense(self, name: str) -> Optional[Dict]:
        """Create a new Expense name (no financial data)."""
        return self._post_simple_master("/api/expenses", {"name": name})

    def update_expense(self, expense_id: int, name: str) -> Optional[Dict]:
        """Update an existing Expense name."""
        return self._put_simple_master("/api/expenses", {"id": expense_id, "name": name})

    def deactivate_expense(self, expense_id: int) -> Optional[Dict]:
        """Deactivate an Expense name (no delete)."""
        return self._put_simple_master("/api/expenses/deactivate", {"id": expense_id})

    # Vendors

    def get_vendors(self) -> Optional[Dict]:
        """Get all Vendors master names."""
        return self._get_simple_master("/api/vendors")

    def create_vendor(self, name: str) -> Optional[Dict]:
        """Create a new Vendor name (no financial data)."""
        return self._post_simple_master("/api/vendors", {"name": name})

    def update_vendor(self, vendor_id: int, name: str) -> Optional[Dict]:
        """Update an existing Vendor name."""
        return self._put_simple_master("/api/vendors", {"id": vendor_id, "name": name})

    def deactivate_vendor(self, vendor_id: int) -> Optional[Dict]:
        """Deactivate a Vendor name (no delete)."""
        return self._put_simple_master("/api/vendors/deactivate", {"id": vendor_id})
    
    
    def close(self):
        """Close the session and release connections"""
        self.session.close()
    
    def get_current_server(self) -> Optional[str]:
        """Get the currently connected server URL"""
        return self.current_server
    
    def ping(self) -> bool:
        """Ping server to check if it's online (fast check with cached preference)"""
        # Use a very short timeout for ping to avoid freezing
        original_timeout = self.timeout
        self.timeout = 2  # Fast ping timeout
        try:
            response = self._try_request("GET", "/api/ping")
            return response is not None
        finally:
            self.timeout = original_timeout
    
    def health_check(self) -> Optional[Dict]:
        """Get server health status"""
        response = self._try_request("GET", "/api/health")
        if response:
            return response.json()
        return None
    
    def login(self, username: str, password: str) -> Optional[Dict]:
        """Login to server"""
        try:
            response = self._try_request(
                "POST",
                "/api/login",
                json={"username": username, "password": password}
            )
            if response:
                # Check if response is successful
                if 200 <= response.status_code < 300:
                    return response.json()
                else:
                    # Return error response as dict for better error handling
                    try:
                        error_data = response.json()
                        return error_data
                    except:
                        return {"success": False, "message": f"Server error: {response.status_code}"}
            else:
                # Connection failed
                return {"success": False, "message": "Connection error. Unable to reach server."}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {str(e)}"}

