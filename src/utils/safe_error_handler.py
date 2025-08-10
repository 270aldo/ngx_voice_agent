"""
Safe error handler decorator for API endpoints.
Provides automatic error sanitization and consistent error responses.
"""

import functools
import logging
from typing import Callable, Any, Optional, Union
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .error_sanitizer import sanitize_error, safe_error_response

logger = logging.getLogger(__name__)


def safe_endpoint(
    default_status_code: int = 500,
    default_error_message: str = "An error occurred processing your request",
    log_errors: bool = True
):
    """
    Decorator for API endpoints that provides safe error handling.
    
    Features:
    - Automatically sanitizes exceptions
    - Provides consistent error responses
    - Logs full error details internally
    - Prevents sensitive information leakage
    
    Args:
        default_status_code: Default HTTP status code for errors
        default_error_message: Default error message
        log_errors: Whether to log errors
    
    Usage:
        @safe_endpoint()
        async def my_endpoint(request: Request):
            # endpoint logic
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            request = None
            request_id = None
            
            try:
                # Extract request if available
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        request_id = getattr(request.state, "request_id", None)
                        break
                
                # Call the actual endpoint
                return await func(*args, **kwargs)
                
            except HTTPException:
                # Re-raise HTTP exceptions as they're already formatted
                raise
                
            except Exception as e:
                # Build context
                context = {}
                if request:
                    context = {
                        "endpoint": func.__name__,
                        "method": request.method,
                        "path": request.url.path,
                        "query_params": dict(request.query_params)
                    }
                
                # Sanitize error
                sanitized = sanitize_error(e, request_id, context)
                
                # Log if enabled
                if log_errors:
                    logger.error(
                        f"Error in endpoint {func.__name__}: {type(e).__name__}",
                        exc_info=True,
                        extra={
                            "request_id": request_id,
                            "endpoint": func.__name__,
                            "context": context
                        }
                    )
                
                # Return safe error response
                return JSONResponse(
                    status_code=default_status_code,
                    content={
                        "error": True,
                        "error_code": sanitized.error_code,
                        "message": sanitized.user_message,
                        "request_id": sanitized.request_id,
                        "timestamp": sanitized.timestamp
                    }
                )
        
        return wrapper
    return decorator


def safe_service_call(
    service_name: str,
    fallback_value: Any = None,
    raise_on_error: bool = False
):
    """
    Decorator for service method calls with error handling.
    
    Args:
        service_name: Name of the service for logging
        fallback_value: Value to return on error
        raise_on_error: Whether to re-raise exceptions
    
    Usage:
        @safe_service_call("ml_predictor", fallback_value={"score": 0.5})
        async def predict_score(self, data):
            # prediction logic
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
                
            except Exception as e:
                logger.error(
                    f"Error in service {service_name}.{func.__name__}: {type(e).__name__}",
                    exc_info=True
                )
                
                if raise_on_error:
                    raise
                
                return fallback_value
        
        return wrapper
    return decorator


class SafeErrorContext:
    """
    Context manager for safe error handling in code blocks.
    
    Usage:
        async with SafeErrorContext("processing_message") as ctx:
            # code that might raise exceptions
            result = await risky_operation()
            
        if ctx.error_occurred:
            # handle error case
            return ctx.fallback_value
    """
    
    def __init__(
        self,
        operation_name: str,
        fallback_value: Any = None,
        log_errors: bool = True,
        request_id: Optional[str] = None
    ):
        self.operation_name = operation_name
        self.fallback_value = fallback_value
        self.log_errors = log_errors
        self.request_id = request_id
        self.error_occurred = False
        self.error = None
        self.sanitized_error = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.error_occurred = True
            self.error = exc_val
            
            # Sanitize error
            context = {"operation": self.operation_name}
            self.sanitized_error = sanitize_error(exc_val, self.request_id, context)
            
            # Log if enabled
            if self.log_errors:
                logger.error(
                    f"Error in operation {self.operation_name}: {type(exc_val).__name__}",
                    exc_info=(exc_type, exc_val, exc_tb),
                    extra={
                        "request_id": self.request_id,
                        "operation": self.operation_name
                    }
                )
            
            # Suppress exception
            return True
        
        return False
    
    def get_error_response(self, status_code: int = 500) -> dict:
        """Get a safe error response if an error occurred."""
        if not self.error_occurred or not self.sanitized_error:
            return None
        
        return {
            "error": True,
            "error_code": self.sanitized_error.error_code,
            "message": self.sanitized_error.user_message,
            "request_id": self.sanitized_error.request_id,
            "timestamp": self.sanitized_error.timestamp
        }