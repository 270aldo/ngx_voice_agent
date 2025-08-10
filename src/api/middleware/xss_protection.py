"""
XSS Protection Middleware.

This middleware automatically sanitizes incoming request data to prevent
Cross-Site Scripting (XSS) attacks.
"""

import json
import logging
import re
from typing import Callable, Any, Dict, List, Union
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import MutableHeaders

from src.utils.sanitization import (
    InputSanitizer, 
    sanitize_request_data,
    create_safe_markdown
)

logger = logging.getLogger(__name__)


class XSSProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to protect against XSS attacks by sanitizing inputs.
    """
    
    def __init__(self, app, 
                 sanitize_query_params: bool = True,
                 sanitize_headers: bool = True,
                 sanitize_json: bool = True,
                 sanitize_form_data: bool = True,
                 log_violations: bool = True,
                 custom_headers: Dict[str, str] = None):
        """
        Initialize XSS protection middleware.
        
        Args:
            app: FastAPI application
            sanitize_query_params: Sanitize URL query parameters
            sanitize_headers: Sanitize request headers
            sanitize_json: Sanitize JSON request bodies
            sanitize_form_data: Sanitize form data
            log_violations: Log detected XSS attempts
            custom_headers: Additional security headers to add
        """
        super().__init__(app)
        self.sanitize_query_params = sanitize_query_params
        self.sanitize_headers = sanitize_headers
        self.sanitize_json = sanitize_json
        self.sanitize_form_data = sanitize_form_data
        self.log_violations = log_violations
        self.custom_headers = custom_headers or {}
        self.sanitizer = InputSanitizer()
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with XSS protection.
        """
        violations = []
        
        try:
            # Check and sanitize query parameters
            if self.sanitize_query_params and request.query_params:
                sanitized_params = {}
                has_violations = False
                for key, value in request.query_params.items():
                    clean_key = self.sanitizer.sanitize_text(key)
                    clean_value = self.sanitizer.sanitize_text(value)
                    
                    if clean_key != key or clean_value != value:
                        violations.append(f"Query param: {key}={value}")
                        has_violations = True
                    
                    sanitized_params[clean_key] = clean_value
                
                # Update request with sanitized params
                request._query_params = sanitized_params
            
            # Check and sanitize headers
            if self.sanitize_headers:
                dangerous_headers = ['referer', 'user-agent', 'x-forwarded-for']
                headers = dict(request.headers)
                
                for header in dangerous_headers:
                    if header in headers:
                        original = headers[header]
                        sanitized = self.sanitizer.sanitize_text(original, max_length=1000)
                        if original != sanitized:
                            violations.append(f"Header {header}: {original[:50]}...")
            
            # Check content type for body sanitization
            content_type = request.headers.get('content-type', '')
            
            # Sanitize request body if needed
            if request.method in ['POST', 'PUT', 'PATCH']:
                body = await request.body()
                
                if body and 'application/json' in content_type and self.sanitize_json:
                    try:
                        data = json.loads(body)
                        sanitized_data = sanitize_request_data(data)
                        
                        # Check for violations
                        if data != sanitized_data:
                            violations.append("JSON body contains potentially dangerous content")
                        
                        # Store sanitized data for endpoint to use
                        request._json = sanitized_data
                        
                    except json.JSONDecodeError:
                        logger.warning("Invalid JSON in request body")
                
                elif body and 'application/x-www-form-urlencoded' in content_type and self.sanitize_form_data:
                    # Handle form data
                    form_data = await request.form()
                    sanitized_form = {}
                    
                    for key, value in form_data.items():
                        clean_key = self.sanitizer.sanitize_text(key)
                        clean_value = self.sanitizer.sanitize_text(str(value))
                        
                        if clean_key != key or clean_value != str(value):
                            violations.append(f"Form field: {key}")
                        
                        sanitized_form[clean_key] = clean_value
                    
                    request._form = sanitized_form
            
            # Log violations if any
            if violations and self.log_violations:
                logger.warning(
                    f"XSS protection triggered for {request.method} {request.url.path}",
                    extra={
                        "violations": violations,
                        "client_ip": request.client.host if request.client else None,
                        "user_agent": request.headers.get('user-agent', 'Unknown')
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add security headers to response
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["X-Content-Type-Options"] = "nosniff"
            
            # Add custom headers
            for header, value in self.custom_headers.items():
                response.headers[header] = value
            
            return response
            
        except Exception as e:
            logger.error(f"Error in XSS protection middleware: {e}", exc_info=True)
            # Don't block request on middleware error
            return await call_next(request)


class ContentSecurityPolicyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set Content Security Policy headers.
    """
    
    def __init__(self, app, policy: Dict[str, str] = None):
        """
        Initialize CSP middleware.
        
        Args:
            app: FastAPI application
            policy: CSP directives
        """
        super().__init__(app)
        
        # Default restrictive policy
        self.policy = policy or {
            "default-src": "'self'",
            "script-src": "'self' 'unsafe-inline' 'unsafe-eval'",  # Adjust based on needs
            "style-src": "'self' 'unsafe-inline'",
            "img-src": "'self' data: https:",
            "font-src": "'self'",
            "connect-src": "'self'",
            "frame-ancestors": "'none'",
            "base-uri": "'self'",
            "form-action": "'self'"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add CSP headers to response.
        """
        response = await call_next(request)
        
        # Build CSP header
        csp_parts = []
        for directive, value in self.policy.items():
            csp_parts.append(f"{directive} {value}")
        
        csp_header = "; ".join(csp_parts)
        response.headers["Content-Security-Policy"] = csp_header
        
        return response


def validate_and_sanitize_input(
    data: Any,
    field_rules: Dict[str, Dict[str, Any]] = None
) -> tuple[Any, List[str]]:
    """
    Validate and sanitize input data based on field rules.
    
    Args:
        data: Input data to validate and sanitize
        field_rules: Rules for specific fields
        
    Returns:
        Tuple of (sanitized_data, errors)
    """
    errors = []
    sanitizer = InputSanitizer()
    
    if not field_rules:
        # Just sanitize without specific rules
        return sanitize_request_data(data), errors
    
    def _process_field(value: Any, rules: Dict[str, Any]) -> Any:
        field_type = rules.get('type', 'text')
        required = rules.get('required', False)
        max_length = rules.get('max_length')
        min_length = rules.get('min_length')
        pattern = rules.get('pattern')
        
        # Check required
        if required and not value:
            errors.append(f"Field is required")
            return None
        
        if not value:
            return None
        
        # Sanitize based on type
        if field_type == 'email':
            sanitized = sanitizer.sanitize_email(str(value))
            if not sanitized:
                errors.append("Invalid email format")
                return None
        elif field_type == 'phone':
            sanitized = sanitizer.sanitize_phone(str(value))
            if not sanitized:
                errors.append("Invalid phone format")
                return None
        elif field_type == 'url':
            sanitized = sanitizer.sanitize_url(str(value))
            if not sanitized:
                errors.append("Invalid URL format")
                return None
        elif field_type == 'html':
            sanitized = sanitizer.sanitize_html(str(value))
        elif field_type == 'filename':
            sanitized = sanitizer.sanitize_filename(str(value))
        else:
            # For text type, respect max_length during sanitization
            sanitized = sanitizer.sanitize_text(str(value), max_length)
        
        # Check length constraints after sanitization
        if sanitized:
            if min_length and len(sanitized) < min_length:
                errors.append(f"Minimum length is {min_length}")
            
            if max_length and field_type != 'text' and len(sanitized) > max_length:
                # Only check max_length for non-text types since text already handles it
                errors.append(f"Maximum length is {max_length}")
        
        # Check pattern
        if pattern and sanitized and not re.match(pattern, sanitized):
            errors.append("Invalid format")
        
        return sanitized
    
    if isinstance(data, dict):
        sanitized = {}
        for field, value in data.items():
            if field in field_rules:
                sanitized[field] = _process_field(value, field_rules[field])
            else:
                # No rules, just sanitize
                sanitized[field] = sanitizer.sanitize_text(str(value)) if value else None
        return sanitized, errors
    else:
        return sanitize_request_data(data), errors


# Pre-configured middleware instances
def create_xss_protection_middleware(app):
    """Create XSS protection middleware with default settings."""
    return XSSProtectionMiddleware(
        app,
        sanitize_query_params=True,
        sanitize_headers=True,
        sanitize_json=True,
        sanitize_form_data=True,
        log_violations=True,
        custom_headers={
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
    )


def create_csp_middleware(app, production: bool = False):
    """Create CSP middleware with environment-specific settings."""
    if production:
        # Stricter policy for production
        policy = {
            "default-src": "'none'",
            "script-src": "'self'",
            "style-src": "'self'",
            "img-src": "'self' data: https:",
            "font-src": "'self'",
            "connect-src": "'self'",
            "frame-ancestors": "'none'",
            "base-uri": "'self'",
            "form-action": "'self'",
            "upgrade-insecure-requests": ""
        }
    else:
        # More permissive for development
        policy = {
            "default-src": "'self'",
            "script-src": "'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src": "'self' 'unsafe-inline'",
            "img-src": "'self' data: https: http:",
            "font-src": "'self' data:",
            "connect-src": "'self' http: https: ws: wss:",
            "frame-ancestors": "'self'",
            "base-uri": "'self'"
        }
    
    return ContentSecurityPolicyMiddleware(app, policy)