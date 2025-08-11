"""
Custom logging filters for the application.

This module provides custom filters to control what gets logged,
particularly useful for filtering out noisy health check requests.
"""

import logging
from typing import Any


class HealthCheckFilter(logging.Filter):
    """
    Filter to exclude health check endpoint logs.
    
    This prevents the logs from being flooded with health check requests
    from monitoring systems, load balancers, etc.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determine if the record should be logged.
        
        Args:
            record: The log record to evaluate
            
        Returns:
            True if the record should be logged, False otherwise
        """
        # Filter out health check endpoints
        if hasattr(record, 'args') and record.args:
            # Check for common health check patterns in log messages
            message = record.getMessage()
            health_patterns = [
                '/health',
                '/healthz',
                '/ready',
                '/alive',
                'GET /health',
                'GET /healthz',
            ]
            
            for pattern in health_patterns:
                if pattern in message:
                    return False
        
        return True


class SensitiveDataFilter(logging.Filter):
    """
    Filter to redact sensitive data from logs.
    
    This helps prevent accidental logging of API keys, tokens,
    passwords, and other sensitive information.
    """
    
    # Patterns to redact
    SENSITIVE_PATTERNS = [
        'api_key',
        'apikey',
        'api-key',
        'password',
        'pwd',
        'secret',
        'token',
        'authorization',
        'bearer',
        'jwt',
        'session',
        'cookie',
        'supabase_key',
        'openai_key',
        'elevenlabs_key',
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter and redact sensitive data from log records.
        
        Args:
            record: The log record to process
            
        Returns:
            True (always logs, but with redacted content)
        """
        # Redact sensitive data in the message
        if hasattr(record, 'msg'):
            record.msg = self._redact_message(str(record.msg))
        
        # Redact sensitive data in arguments
        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                self._redact_message(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        
        return True
    
    def _redact_message(self, message: str) -> str:
        """
        Redact sensitive information from a message.
        
        Args:
            message: The message to redact
            
        Returns:
            The redacted message
        """
        import re
        
        lower_message = message.lower()
        
        # Check for sensitive patterns
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in lower_message:
                # Redact values after equals signs or colons
                message = re.sub(
                    rf'({pattern}["\']?\s*[:=]\s*["\']?)([^"\'\s,}}]+)',
                    r'\1[REDACTED]',
                    message,
                    flags=re.IGNORECASE
                )
                
                # Redact values in headers
                message = re.sub(
                    rf'({pattern}["\']?\s*:\s*["\']?)([^"\'\s,}}]+)',
                    r'\1[REDACTED]',
                    message,
                    flags=re.IGNORECASE
                )
        
        # Redact JWT tokens
        message = re.sub(
            r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',
            '[JWT_REDACTED]',
            message
        )
        
        # Redact API keys that look like UUIDs or long strings
        message = re.sub(
            r'\b[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}\b',
            '[UUID_REDACTED]',
            message
        )
        
        # Redact sk- prefixed keys (OpenAI style)
        message = re.sub(
            r'\bsk-[A-Za-z0-9]{48}\b',
            '[SK_KEY_REDACTED]',
            message
        )
        
        return message


class PerformanceFilter(logging.Filter):
    """
    Filter to add performance metrics to log records.
    
    This adds timing information and request IDs for performance monitoring.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add performance context to log records.
        
        Args:
            record: The log record to enhance
            
        Returns:
            True (always logs)
        """
        import time
        import threading
        
        # Add timestamp in milliseconds
        record.timestamp_ms = int(time.time() * 1000)
        
        # Add thread information
        record.thread_name = threading.current_thread().name
        
        # Add memory usage if available
        try:
            import psutil
            process = psutil.Process()
            record.memory_mb = process.memory_info().rss / 1024 / 1024
        except (ImportError, AttributeError, OSError) as e:
            logger.debug(f"Failed to get memory info: {e}")
            record.memory_mb = 0
        
        return True


class ErrorContextFilter(logging.Filter):
    """
    Filter to enhance error logs with additional context.
    
    This adds stack traces, local variables, and other debugging information
    to error-level logs.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Enhance error records with additional context.
        
        Args:
            record: The log record to enhance
            
        Returns:
            True (always logs)
        """
        if record.levelno >= logging.ERROR:
            import traceback
            import sys
            
            # Add full stack trace if available
            if sys.exc_info()[0] is not None:
                record.full_stack_trace = traceback.format_exc()
            
            # Add request context if available
            # This would be populated by middleware
            record.request_id = getattr(record, 'request_id', 'N/A')
            record.user_id = getattr(record, 'user_id', 'N/A')
            
        return True