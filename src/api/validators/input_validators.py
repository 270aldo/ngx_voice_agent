"""
Input Validators

Comprehensive input validation for API endpoints.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field, validator, EmailStr, HttpUrl
from enum import Enum

from src.utils.exception_types import ValidationError


class SanitizationLevel(str, Enum):
    """Levels of input sanitization."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    STRICT = "strict"


class InputSanitizer:
    """Sanitizes and validates user inputs."""
    
    # Dangerous patterns to detect
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',                 # JavaScript protocol
        r'on\w+\s*=',                  # Event handlers
        r'<iframe[^>]*>',              # iframes
        r'<object[^>]*>',              # Object tags
        r'<embed[^>]*>',               # Embed tags
        r'<applet[^>]*>',              # Applet tags
        r'<form[^>]*>',                # Form tags
        r'<link[^>]*>',                # Link tags
        r'<meta[^>]*>',                # Meta tags
        r'<!--.*?-->',                 # HTML comments
        r'<\?.*?\?>',                  # PHP tags
        r'<%.*?%>',                    # ASP tags
    ]
    
    # SQL injection patterns
    SQL_PATTERNS = [
        r'\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b',
        r'--',  # SQL comment
        r'/\*.*?\*/',  # Multi-line SQL comment
        r'\b(OR|AND)\s+\d+\s*=\s*\d+',  # SQL tautology
        r"'\s*(OR|AND)\s+'",  # SQL string injection
    ]
    
    # Command injection patterns
    COMMAND_PATTERNS = [
        r'[;&|`$]',  # Shell metacharacters
        r'\$\(',     # Command substitution
        r'\b(sh|bash|cmd|powershell)\b',  # Shell commands
    ]
    
    @classmethod
    def sanitize_html(cls, input_str: str) -> str:
        """
        Remove potentially dangerous HTML/JavaScript.
        
        Args:
            input_str: Input string to sanitize
            
        Returns:
            Sanitized string
        """
        if not input_str:
            return input_str
        
        # Remove dangerous patterns
        sanitized = input_str
        for pattern in cls.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Escape remaining HTML entities
        sanitized = sanitized.replace('<', '&lt;')
        sanitized = sanitized.replace('>', '&gt;')
        sanitized = sanitized.replace('"', '&quot;')
        sanitized = sanitized.replace("'", '&#x27;')
        
        return sanitized
    
    @classmethod
    def detect_sql_injection(cls, input_str: str) -> bool:
        """
        Detect potential SQL injection attempts.
        
        Args:
            input_str: Input string to check
            
        Returns:
            True if SQL injection detected
        """
        if not input_str:
            return False
        
        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def detect_command_injection(cls, input_str: str) -> bool:
        """
        Detect potential command injection attempts.
        
        Args:
            input_str: Input string to check
            
        Returns:
            True if command injection detected
        """
        if not input_str:
            return False
        
        for pattern in cls.COMMAND_PATTERNS:
            if re.search(pattern, input_str):
                return True
        
        return False
    
    @classmethod
    def sanitize_string(
        cls,
        input_str: str,
        max_length: int = 1000,
        level: SanitizationLevel = SanitizationLevel.STANDARD
    ) -> str:
        """
        Sanitize a string input.
        
        Args:
            input_str: Input string
            max_length: Maximum allowed length
            level: Sanitization level
            
        Returns:
            Sanitized string
            
        Raises:
            ValidationError: If input is dangerous
        """
        if not input_str:
            return ""
        
        # Truncate to max length
        sanitized = input_str[:max_length]
        
        if level == SanitizationLevel.MINIMAL:
            # Just truncate
            return sanitized
        
        # Check for SQL injection
        if cls.detect_sql_injection(sanitized):
            raise ValidationError("Potential SQL injection detected")
        
        # Check for command injection
        if cls.detect_command_injection(sanitized):
            raise ValidationError("Potential command injection detected")
        
        if level == SanitizationLevel.STANDARD:
            # Remove HTML/JS
            sanitized = cls.sanitize_html(sanitized)
        
        elif level == SanitizationLevel.STRICT:
            # Remove HTML/JS and restrict to alphanumeric + basic punctuation
            sanitized = cls.sanitize_html(sanitized)
            # Allow only safe characters
            sanitized = re.sub(r'[^a-zA-Z0-9\s\-_.,!?@#$%&*()+=/]', '', sanitized)
        
        return sanitized.strip()


# Pydantic Models for Request Validation

class ConversationStartRequest(BaseModel):
    """Request model for starting a conversation."""
    customer_name: str = Field(..., min_length=1, max_length=100)
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = Field(None, pattern=r'^\+?[\d\s\-()]+$', max_length=20)
    initial_message: Optional[str] = Field(None, max_length=1000)
    platform: Optional[str] = Field(None, max_length=50)
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('customer_name')
    def validate_name(cls, v):
        """Validate and sanitize customer name."""
        sanitized = InputSanitizer.sanitize_string(v, max_length=100, level=SanitizationLevel.STRICT)
        if len(sanitized) < 1:
            raise ValueError("Customer name is required")
        return sanitized
    
    @validator('initial_message')
    def validate_message(cls, v):
        """Validate and sanitize initial message."""
        if v:
            return InputSanitizer.sanitize_string(v, max_length=1000)
        return v
    
    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata size."""
        if v and len(str(v)) > 10000:
            raise ValueError("Metadata too large")
        return v


class MessageRequest(BaseModel):
    """Request model for sending a message."""
    conversation_id: str = Field(..., pattern=r'^[a-f0-9\-]{36}$')  # UUID format
    message: str = Field(..., min_length=1, max_length=4000)
    voice_enabled: bool = Field(False)
    
    @validator('message')
    def validate_message(cls, v):
        """Validate and sanitize message."""
        sanitized = InputSanitizer.sanitize_string(v, max_length=4000)
        if len(sanitized) < 1:
            raise ValueError("Message cannot be empty")
        return sanitized


class QualificationRequest(BaseModel):
    """Request model for lead qualification."""
    conversation_id: str = Field(..., pattern=r'^[a-f0-9\-]{36}$')
    responses: Dict[str, str]
    
    @validator('responses')
    def validate_responses(cls, v):
        """Validate qualification responses."""
        if not v:
            raise ValueError("Responses are required")
        
        # Sanitize all response values
        sanitized = {}
        for key, value in v.items():
            if not isinstance(key, str) or len(key) > 50:
                raise ValueError(f"Invalid response key: {key}")
            if not isinstance(value, str):
                raise ValueError(f"Response value must be string: {key}")
            
            sanitized[key] = InputSanitizer.sanitize_string(value, max_length=500)
        
        return sanitized


class AnalyticsRequest(BaseModel):
    """Request model for analytics queries."""
    start_date: datetime
    end_date: datetime
    metrics: List[str] = Field(..., min_items=1, max_items=20)
    group_by: Optional[str] = Field(None, pattern=r'^[a-z_]+$')
    filters: Optional[Dict[str, Any]] = None
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate date range."""
        if 'start_date' in values and v < values['start_date']:
            raise ValueError("End date must be after start date")
        
        # Maximum 90 days range
        if 'start_date' in values:
            delta = v - values['start_date']
            if delta.days > 90:
                raise ValueError("Date range cannot exceed 90 days")
        
        return v
    
    @validator('metrics')
    def validate_metrics(cls, v):
        """Validate requested metrics."""
        allowed_metrics = [
            'conversations', 'messages', 'conversions', 'response_time',
            'sentiment', 'qualification_rate', 'transfer_rate'
        ]
        
        for metric in v:
            if metric not in allowed_metrics:
                raise ValueError(f"Invalid metric: {metric}")
        
        return v


class WebhookRequest(BaseModel):
    """Request model for webhook endpoints."""
    event_type: str = Field(..., max_length=50)
    payload: Dict[str, Any]
    signature: str = Field(..., min_length=32, max_length=256)
    timestamp: datetime
    
    @validator('event_type')
    def validate_event_type(cls, v):
        """Validate event type."""
        allowed_events = [
            'conversation.started', 'conversation.ended',
            'message.sent', 'message.received',
            'transfer.requested', 'qualification.completed'
        ]
        
        if v not in allowed_events:
            raise ValueError(f"Invalid event type: {v}")
        
        return v
    
    @validator('payload')
    def validate_payload(cls, v):
        """Validate payload size."""
        if len(str(v)) > 100000:  # 100KB limit
            raise ValueError("Payload too large")
        return v


class FileUploadValidator:
    """Validator for file uploads."""
    
    ALLOWED_EXTENSIONS = {
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
        'document': ['.pdf', '.doc', '.docx', '.txt'],
        'audio': ['.mp3', '.wav', '.m4a', '.ogg']
    }
    
    MAX_FILE_SIZES = {
        'image': 5 * 1024 * 1024,      # 5MB
        'document': 10 * 1024 * 1024,  # 10MB
        'audio': 20 * 1024 * 1024      # 20MB
    }
    
    @classmethod
    def validate_file(
        cls,
        filename: str,
        content_type: str,
        file_size: int,
        file_type: str = 'document'
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file.
        
        Args:
            filename: Name of the file
            content_type: MIME type
            file_size: Size in bytes
            file_type: Type category
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file extension
        import os
        ext = os.path.splitext(filename)[1].lower()
        
        if file_type not in cls.ALLOWED_EXTENSIONS:
            return False, f"Invalid file type: {file_type}"
        
        if ext not in cls.ALLOWED_EXTENSIONS[file_type]:
            return False, f"File extension not allowed: {ext}"
        
        # Check file size
        max_size = cls.MAX_FILE_SIZES.get(file_type, 10 * 1024 * 1024)
        if file_size > max_size:
            return False, f"File too large (max {max_size // (1024*1024)}MB)"
        
        # Validate content type
        expected_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain'
        }
        
        if ext in expected_types and content_type != expected_types[ext]:
            return False, f"Content type mismatch for {ext}"
        
        return True, None


class RateLimitValidator:
    """Validator for rate limit headers."""
    
    @staticmethod
    def validate_rate_limit_headers(headers: Dict[str, str]) -> bool:
        """
        Validate rate limit headers.
        
        Args:
            headers: Request headers
            
        Returns:
            True if within limits
        """
        remaining = headers.get('X-RateLimit-Remaining')
        if remaining and int(remaining) <= 0:
            return False
        
        return True


# Export validators
__all__ = [
    'InputSanitizer',
    'SanitizationLevel',
    'ConversationStartRequest',
    'MessageRequest',
    'QualificationRequest',
    'AnalyticsRequest',
    'WebhookRequest',
    'FileUploadValidator',
    'RateLimitValidator'
]