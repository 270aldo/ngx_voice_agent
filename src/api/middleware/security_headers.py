"""
Security Headers Middleware for NGX Voice Sales Agent.

This middleware adds security headers to all HTTP responses to protect
against common web vulnerabilities.
"""

from typing import Callable
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
import asyncio


async def security_headers_middleware(request: Request, call_next: Callable) -> Response:
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Handle StreamingResponse differently
    if isinstance(response, StreamingResponse):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
    
    # For regular responses
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }
    
    # Content Security Policy
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data: https:",
        "connect-src 'self' https://api.openai.com https://api.elevenlabs.io wss:",
        "media-src 'self' https:",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "upgrade-insecure-requests"
    ]
    headers["Content-Security-Policy"] = "; ".join(csp_directives)
    
    # Permissions Policy
    permissions = [
        "camera=(self)",
        "microphone=(self)",
        "geolocation=(self)",
        "payment=()",
        "usb=()",
        "magnetometer=()",
        "gyroscope=()",
        "accelerometer=()"
    ]
    headers["Permissions-Policy"] = ", ".join(permissions)
    
    # Add headers to response
    for key, value in headers.items():
        response.headers[key] = value
    
    return response


def add_security_headers(app):
    """Helper function to add security headers middleware to the app."""
    @app.middleware("http")
    async def _security_headers(request: Request, call_next: Callable) -> Response:
        return await security_headers_middleware(request, call_next)