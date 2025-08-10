"""
CSRF Protection Middleware for NGX Voice Sales Agent

Implements Cross-Site Request Forgery protection using double-submit cookie pattern
with synchronized tokens for secure state-changing operations.
"""

import secrets
import time
import hashlib
import hmac
from typing import Optional, Dict, Any
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from src.config.settings import settings
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)


class CSRFProtectionConfig:
    """Configuration for CSRF protection."""
    
    def __init__(
        self,
        token_length: int = 32,
        token_ttl: int = 3600,  # 1 hour
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        exempt_methods: tuple = ("GET", "HEAD", "OPTIONS", "TRACE"),
        exempt_paths: list = None,
        secure_cookie: bool = True,
        same_site: str = "strict"
    ):
        self.token_length = token_length
        self.token_ttl = token_ttl
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.exempt_methods = exempt_methods
        self.exempt_paths = exempt_paths or []
        self.secure_cookie = secure_cookie
        self.same_site = same_site


class CSRFTokenManager:
    """Manages CSRF token generation, validation and storage."""
    
    def __init__(self, config: CSRFProtectionConfig):
        self.config = config
        self.tokens: Dict[str, float] = {}  # token -> expiry_time
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def generate_token(self) -> str:
        """Generate a new CSRF token."""
        # Create base token
        base_token = secrets.token_urlsafe(self.config.token_length)
        timestamp = str(int(time.time()))
        
        # Create HMAC signature
        secret_key = getattr(settings, 'csrf_secret_key', None)
        if secret_key and hasattr(secret_key, 'get_secret_value'):
            secret = secret_key.get_secret_value()
        else:
            jwt_secret = getattr(settings, 'jwt_secret', None)
            if jwt_secret and hasattr(jwt_secret, 'get_secret_value'):
                secret = jwt_secret.get_secret_value()
            else:
                secret = 'default-csrf-secret'
        signature = hmac.new(
            secret.encode(),
            f"{base_token}:{timestamp}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Combine token with timestamp and signature
        token = f"{base_token}:{timestamp}:{signature}"
        
        # Store token with expiry
        expiry_time = time.time() + self.config.token_ttl
        self.tokens[token] = expiry_time
        
        # Cleanup old tokens periodically
        self._cleanup_expired_tokens()
        
        return token
    
    def validate_token(self, token: str) -> bool:
        """Validate a CSRF token."""
        if not token:
            return False
        
        try:
            # Parse token components
            parts = token.split(':')
            if len(parts) != 3:
                return False
            
            base_token, timestamp, signature = parts
            
            # Verify HMAC signature
            secret_key = getattr(settings, 'csrf_secret_key', None)
            if secret_key and hasattr(secret_key, 'get_secret_value'):
                secret = secret_key.get_secret_value()
            else:
                jwt_secret = getattr(settings, 'jwt_secret', None)
                if jwt_secret and hasattr(jwt_secret, 'get_secret_value'):
                    secret = jwt_secret.get_secret_value()
                else:
                    secret = 'default-csrf-secret'
            expected_signature = hmac.new(
                secret.encode(),
                f"{base_token}:{timestamp}".encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return False
            
            # Check if token exists and is not expired
            if token not in self.tokens:
                return False
            
            if time.time() > self.tokens[token]:
                # Token expired, remove it
                del self.tokens[token]
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"CSRF token validation error: {e}")
            return False
    
    def revoke_token(self, token: str):
        """Revoke a specific token."""
        if token in self.tokens:
            del self.tokens[token]
    
    def _cleanup_expired_tokens(self):
        """Remove expired tokens from storage."""
        current_time = time.time()
        
        # Only cleanup periodically to avoid performance impact
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = current_time
        
        expired_tokens = [
            token for token, expiry in self.tokens.items()
            if current_time > expiry
        ]
        
        for token in expired_tokens:
            del self.tokens[token]
        
        if expired_tokens:
            logger.debug(f"Cleaned up {len(expired_tokens)} expired CSRF tokens")


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF Protection Middleware using double-submit cookie pattern."""
    
    def __init__(self, app, config: Optional[CSRFProtectionConfig] = None):
        super().__init__(app)
        self.config = config or CSRFProtectionConfig()
        self.token_manager = CSRFTokenManager(self.config)
    
    def _is_exempt(self, request: Request) -> bool:
        """Check if request is exempt from CSRF protection."""
        # Check HTTP method
        if request.method in self.config.exempt_methods:
            return True
        
        # Check path exemptions
        path = request.url.path
        for exempt_path in self.config.exempt_paths:
            if path.startswith(exempt_path):
                return True
        
        return False
    
    def _get_token_from_request(self, request: Request) -> Optional[str]:
        """Extract CSRF token from request headers or form data."""
        # Check header first
        token = request.headers.get(self.config.header_name)
        if token:
            return token
        
        # For form data, check if it's available in request state
        # This would need to be populated by form parsing middleware
        form_token = getattr(request.state, 'csrf_token', None)
        return form_token
    
    async def dispatch(self, request: Request, call_next):
        """Process request with CSRF protection."""
        # Skip if request is exempt
        if self._is_exempt(request):
            response = await call_next(request)
            return response
        
        # Get tokens from cookie and request
        cookie_token = request.cookies.get(self.config.cookie_name)
        request_token = self._get_token_from_request(request)
        
        # Validate CSRF protection
        if not cookie_token or not request_token:
            logger.warning(f"CSRF validation failed: missing tokens for {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing"
            )
        
        if cookie_token != request_token:
            logger.warning(f"CSRF validation failed: token mismatch for {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token mismatch"
            )
        
        if not self.token_manager.validate_token(cookie_token):
            logger.warning(f"CSRF validation failed: invalid token for {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token invalid or expired"
            )
        
        # Process request
        response = await call_next(request)
        return response
    
    def generate_token_response(self, response: Response) -> str:
        """Generate and set CSRF token in response."""
        token = self.token_manager.generate_token()
        
        # Set cookie with security flags
        response.set_cookie(
            key=self.config.cookie_name,
            value=token,
            max_age=self.config.token_ttl,
            secure=self.config.secure_cookie,
            httponly=False,  # Frontend needs to read this
            samesite=self.config.same_site
        )
        
        return token


# Global CSRF protection instance
csrf_config = CSRFProtectionConfig(
    exempt_paths=[
        "/health",
        "/docs",
        "/openapi.json",
        "/api/v1/auth/csrf",  # CSRF endpoint itself is exempt
        "/api/v1/ws"  # WebSocket connections
    ]
)

csrf_protection = CSRFProtectionMiddleware(None, csrf_config)