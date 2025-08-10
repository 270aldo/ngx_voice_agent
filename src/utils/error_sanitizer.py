"""
Error Sanitizer - Sanitizes error messages and stack traces before exposure.
Prevents sensitive information leakage in error responses.
"""

import re
import logging
import traceback
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SanitizedError:
    """Sanitized error information safe for external exposure."""
    error_code: str
    message: str
    severity: ErrorSeverity
    request_id: Optional[str] = None
    timestamp: Optional[str] = None
    user_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "user_message": self.user_message or self.message
        }


class ErrorSanitizer:
    """
    Sanitizes error messages and stack traces to prevent information leakage.
    
    Features:
    - Removes sensitive file paths
    - Redacts credentials and tokens
    - Sanitizes database connection strings
    - Provides user-friendly error messages
    - Logs full error details internally
    """
    
    # Patterns for sensitive information
    SENSITIVE_PATTERNS = [
        # File paths
        (r'/Users/[^/\s]+', '/Users/***'),
        (r'/home/[^/\s]+', '/home/***'),
        (r'C:\\\\Users\\\\[^\\\\s]+', 'C:\\\\Users\\\\***'),
        (r'/var/www/[^/\s]+', '/var/www/***'),
        
        # Database URLs
        (r'postgresql://[^@]+@[^/\s]+', 'postgresql://***:***@***'),
        (r'mysql://[^@]+@[^/\s]+', 'mysql://***:***@***'),
        (r'mongodb://[^@]+@[^/\s]+', 'mongodb://***:***@***'),
        (r'redis://[^@]+@[^/\s]+', 'redis://***:***@***'),
        
        # API Keys and Tokens
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?[\w-]+', 'api_key=***'),
        (r'token["\']?\s*[:=]\s*["\']?[\w-]+', 'token=***'),
        (r'bearer\s+[\w-]+', 'bearer ***'),
        (r'sk-[a-zA-Z0-9]{48}', 'sk-***'),  # OpenAI style
        (r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '***-***-***-***-***'),  # UUID
        
        # Passwords
        (r'password["\']?\s*[:=]\s*["\']?[^"\'\s]+', 'password=***'),
        (r'pwd["\']?\s*[:=]\s*["\']?[^"\'\s]+', 'pwd=***'),
        
        # IP Addresses
        (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '***.***.***.***'),
        
        # Email addresses in error context
        (r'[\w\.-]+@[\w\.-]+\.\w+', '***@***.***'),
        
        # Port numbers in connection strings
        (r':(\d{4,5})', ':****'),
        
        # AWS/Cloud credentials
        (r'AKIA[0-9A-Z]{16}', 'AKIA****************'),
        (r'aws_access_key_id["\']?\s*[:=]\s*["\']?[\w-]+', 'aws_access_key_id=***'),
        
        # Supabase specific
        (r'supabase_url["\']?\s*[:=]\s*["\']?[^"\'\s]+', 'supabase_url=***'),
        (r'supabase_key["\']?\s*[:=]\s*["\']?[^"\'\s]+', 'supabase_key=***'),
    ]
    
    # Error code mappings
    ERROR_CODES = {
        # Database errors
        "IntegrityError": "DB_INTEGRITY_ERROR",
        "OperationalError": "DB_CONNECTION_ERROR",
        "DataError": "DB_DATA_ERROR",
        "ProgrammingError": "DB_QUERY_ERROR",
        
        # API errors
        "ConnectionError": "API_CONNECTION_ERROR",
        "Timeout": "API_TIMEOUT_ERROR",
        "HTTPError": "API_HTTP_ERROR",
        "RequestException": "API_REQUEST_ERROR",
        
        # Authentication errors
        "AuthenticationError": "AUTH_ERROR",
        "PermissionError": "PERMISSION_ERROR",
        "TokenExpiredError": "TOKEN_EXPIRED",
        
        # Validation errors
        "ValidationError": "VALIDATION_ERROR",
        "ValueError": "INVALID_VALUE_ERROR",
        "TypeError": "TYPE_ERROR",
        
        # System errors
        "MemoryError": "MEMORY_ERROR",
        "OSError": "SYSTEM_ERROR",
        "IOError": "IO_ERROR",
        
        # Application specific
        "ConversationNotFound": "CONVERSATION_NOT_FOUND",
        "ServiceUnavailable": "SERVICE_UNAVAILABLE",
        "RateLimitExceeded": "RATE_LIMIT_ERROR",
    }
    
    # User-friendly messages
    USER_MESSAGES = {
        "DB_INTEGRITY_ERROR": "There was a problem saving your data. Please try again.",
        "DB_CONNECTION_ERROR": "We're having trouble connecting to our database. Please try again in a moment.",
        "DB_DATA_ERROR": "The data provided couldn't be processed. Please check your input.",
        "DB_QUERY_ERROR": "There was an error processing your request. Our team has been notified.",
        
        "API_CONNECTION_ERROR": "We couldn't connect to the required service. Please check your connection.",
        "API_TIMEOUT_ERROR": "The request took too long to complete. Please try again.",
        "API_HTTP_ERROR": "There was a problem with the external service. Please try again later.",
        "API_REQUEST_ERROR": "Your request couldn't be processed. Please try again.",
        
        "AUTH_ERROR": "Authentication failed. Please check your credentials.",
        "PERMISSION_ERROR": "You don't have permission to perform this action.",
        "TOKEN_EXPIRED": "Your session has expired. Please log in again.",
        
        "VALIDATION_ERROR": "The provided data is invalid. Please check your input.",
        "INVALID_VALUE_ERROR": "One or more values are invalid. Please review your input.",
        "TYPE_ERROR": "The data format is incorrect. Please check the documentation.",
        
        "MEMORY_ERROR": "The system is low on resources. Please try again later.",
        "SYSTEM_ERROR": "A system error occurred. Our team has been notified.",
        "IO_ERROR": "There was a problem reading or writing data.",
        
        "CONVERSATION_NOT_FOUND": "The conversation could not be found.",
        "SERVICE_UNAVAILABLE": "This service is temporarily unavailable. Please try again later.",
        "RATE_LIMIT_ERROR": "Too many requests. Please slow down and try again.",
        
        "UNKNOWN_ERROR": "An unexpected error occurred. Please try again or contact support."
    }
    
    def __init__(self, log_full_errors: bool = True):
        """
        Initialize error sanitizer.
        
        Args:
            log_full_errors: Whether to log full error details internally
        """
        self.log_full_errors = log_full_errors
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.SENSITIVE_PATTERNS
        ]
    
    def sanitize_error(
        self,
        error: Exception,
        request_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> SanitizedError:
        """
        Sanitize an error for external exposure.
        
        Args:
            error: The exception to sanitize
            request_id: Optional request ID for tracking
            context: Optional context information
            
        Returns:
            Sanitized error safe for external exposure
        """
        # Log full error internally if enabled
        if self.log_full_errors:
            self._log_full_error(error, request_id, context)
        
        # Get error code and severity
        error_code = self._get_error_code(error)
        severity = self._get_error_severity(error)
        
        # Sanitize error message
        sanitized_message = self._sanitize_message(str(error))
        
        # Get user-friendly message
        user_message = self.USER_MESSAGES.get(error_code, self.USER_MESSAGES["UNKNOWN_ERROR"])
        
        # Create sanitized error
        return SanitizedError(
            error_code=error_code,
            message=sanitized_message,
            severity=severity,
            request_id=request_id,
            timestamp=self._get_timestamp(),
            user_message=user_message
        )
    
    def sanitize_stack_trace(self, stack_trace: str) -> str:
        """
        Sanitize a stack trace for logging.
        
        Args:
            stack_trace: The stack trace to sanitize
            
        Returns:
            Sanitized stack trace
        """
        sanitized = stack_trace
        
        # Apply all sanitization patterns
        for pattern, replacement in self._compiled_patterns:
            sanitized = pattern.sub(replacement, sanitized)
        
        # Remove absolute file paths but keep relative ones
        sanitized = re.sub(r'File "/.+/([^/]+\.py)"', r'File "\1"', sanitized)
        sanitized = re.sub(r'File "[A-Z]:\\.+\\([^\\]+\.py)"', r'File "\1"', sanitized)
        
        return sanitized
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize an error message."""
        sanitized = message
        
        # Apply all sanitization patterns
        for pattern, replacement in self._compiled_patterns:
            sanitized = pattern.sub(replacement, sanitized)
        
        # Truncate if too long
        if len(sanitized) > 500:
            sanitized = sanitized[:497] + "..."
        
        return sanitized
    
    def _get_error_code(self, error: Exception) -> str:
        """Get error code for an exception."""
        error_type = type(error).__name__
        return self.ERROR_CODES.get(error_type, "UNKNOWN_ERROR")
    
    def _get_error_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity."""
        error_type = type(error).__name__
        
        # Critical errors
        if error_type in ["MemoryError", "SystemExit", "KeyboardInterrupt"]:
            return ErrorSeverity.CRITICAL
        
        # High severity
        if error_type in ["OperationalError", "AuthenticationError", "PermissionError"]:
            return ErrorSeverity.HIGH
        
        # Medium severity
        if error_type in ["ValidationError", "ValueError", "TypeError", "ConnectionError"]:
            return ErrorSeverity.MEDIUM
        
        # Default to low
        return ErrorSeverity.LOW
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    def _log_full_error(
        self,
        error: Exception,
        request_id: Optional[str],
        context: Optional[Dict[str, Any]]
    ):
        """Log full error details internally."""
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "request_id": request_id,
            "context": context,
            "stack_trace": traceback.format_exc()
        }
        
        # Log based on severity
        severity = self._get_error_severity(error)
        if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            logger.error("Error occurred", extra=error_details, exc_info=True)
        else:
            logger.warning("Error occurred", extra=error_details)


# Global instance
error_sanitizer = ErrorSanitizer()


def sanitize_error(
    error: Exception,
    request_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> SanitizedError:
    """
    Convenience function to sanitize errors.
    
    Args:
        error: The exception to sanitize
        request_id: Optional request ID
        context: Optional context
        
    Returns:
        Sanitized error
    """
    return error_sanitizer.sanitize_error(error, request_id, context)


def safe_error_response(
    error: Exception,
    status_code: int = 500,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a safe error response for APIs.
    
    Args:
        error: The exception
        status_code: HTTP status code
        request_id: Request ID
        
    Returns:
        Safe error response dictionary
    """
    sanitized = sanitize_error(error, request_id)
    
    return {
        "error": True,
        "status_code": status_code,
        "error_code": sanitized.error_code,
        "message": sanitized.user_message,
        "request_id": sanitized.request_id,
        "timestamp": sanitized.timestamp
    }