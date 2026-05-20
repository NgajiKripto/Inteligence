"""
MemeCoin Intelligence - Utilities
"""

import re
import os
import json
import tempfile
import time
from typing import Optional
from functools import wraps
from flask import request, jsonify

from ..config import Config


def redact_url(url: str) -> str:
    """Redact API keys from URLs before logging"""
    return re.sub(r'(api-key=|api_key=|apikey=)[^&\s]+', r'\1***REDACTED***', url, flags=re.IGNORECASE)


def validate_solana_address(address: str) -> bool:
    """Validate Solana address format (base58, 32-44 chars)"""
    if not address or len(address) < 32 or len(address) > 44:
        return False
    base58_chars = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
    return all(c in base58_chars for c in address)


def validate_evm_address(address: str) -> bool:
    """Validate EVM address format (0x + 40 hex chars)"""
    if not address:
        return False
    return bool(re.match(r'^0x[0-9a-fA-F]{40}$', address))


def validate_contract_address(address: str, chain: str = "solana") -> bool:
    """Validate contract address based on chain"""
    if chain == "solana":
        return validate_solana_address(address)
    elif chain in ("ethereum", "bsc"):
        return validate_evm_address(address)
    return len(address) > 10  # fallback basic check


def atomic_write_json(path: str, data: dict, indent: int = 2):
    """Atomically write JSON to file (write to temp, then rename)"""
    dir_name = os.path.dirname(path)
    os.makedirs(dir_name, exist_ok=True)
    
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=indent, default=str)
        os.replace(tmp_path, path)  # atomic on POSIX
    except Exception:
        # Cleanup temp file on failure
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


# === Rate Limiting ===

class RateLimiter:
    """Simple in-memory rate limiter (per-IP)"""
    
    def __init__(self):
        self._requests = {}  # ip -> [(timestamp, ...)]
        self._cleanup_interval = 60
        self._last_cleanup = time.time()
    
    def is_allowed(self, ip: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
        """Check if request is allowed under rate limit"""
        now = time.time()
        
        # Periodic cleanup
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup(now, window_seconds)
            self._last_cleanup = now
        
        if ip not in self._requests:
            self._requests[ip] = []
        
        # Remove expired entries
        self._requests[ip] = [t for t in self._requests[ip] if now - t < window_seconds]
        
        if len(self._requests[ip]) >= max_requests:
            return False
        
        self._requests[ip].append(now)
        return True
    
    def _cleanup(self, now: float, window: int):
        """Remove old entries"""
        expired_ips = []
        for ip, timestamps in self._requests.items():
            self._requests[ip] = [t for t in timestamps if now - t < window]
            if not self._requests[ip]:
                expired_ips.append(ip)
        for ip in expired_ips:
            del self._requests[ip]


# Global rate limiter instance
rate_limiter = RateLimiter()


def require_api_key(f):
    """
    Decorator to require API key authentication.
    Checks X-API-Key header or api_key query parameter.
    If API_AUTH_KEY is not set in config, auth is skipped (dev mode).
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_key = os.environ.get('API_AUTH_KEY', '')
        
        # If no auth key configured, skip auth (dev mode)
        if not auth_key:
            return f(*args, **kwargs)
        
        # Check header or query param
        provided_key = request.headers.get('X-API-Key', '') or request.args.get('api_key', '')
        
        if not provided_key or provided_key != auth_key:
            return jsonify({
                "success": False,
                "error": "Unauthorized. Provide valid X-API-Key header."
            }), 401
        
        return f(*args, **kwargs)
    return decorated


def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """
    Decorator to apply rate limiting per IP.
    Returns 429 if limit exceeded.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            ip = request.remote_addr or "unknown"
            
            if not rate_limiter.is_allowed(ip, max_requests, window_seconds):
                return jsonify({
                    "success": False,
                    "error": "Rate limit exceeded. Please try again later."
                }), 429
            
            return f(*args, **kwargs)
        return decorated
    return decorator
