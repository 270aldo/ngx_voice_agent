"""
Input Validation Middleware for NGX Voice Sales Agent.
Provides comprehensive validation and sanitization of all incoming requests.
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Set, Union
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from pydantic import BaseModel, Field, field_validator
import html
import urllib.parse
from dataclasses import dataclass
from src.core.constants import ValidationConstants, APIConstants

logger = logging.getLogger(__name__)


@dataclass
class ValidationConfig:
    """Configuration for input validation rules."""
    max_input_length: int = 10000
    max_field_length: int = ValidationConstants.MAX_NAME_LENGTH * 10  # 1000
    max_array_length: int = APIConstants.MAX_PAGE_SIZE
    max_nested_depth: int = 5
    allowed_content_types: Set[str] = None
    blocked_patterns: List[str] = None
    
    def __post_init__(self):
        if self.allowed_content_types is None:
            self.allowed_content_types = {
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data"
            }
        
        if self.blocked_patterns is None:
            # Common injection patterns
            self.blocked_patterns = [
                r"<script[\s\S]*?>[\s\S]*?</script>",  # Script tags
                r"javascript:",  # JavaScript protocol
                r"on\w+\s*=",  # Event handlers
                r"<iframe",  # iframes
                r"<object",  # object tags
                r"<embed",  # embed tags
                r"\$\{.*\}",  # Template injection
                r"{{.*}}",  # Template injection
                r"<%.*%>",  # Server-side template injection
                r"<\?php",  # PHP tags
                r"eval\s*\(",  # eval() calls
                r"exec\s*\(",  # exec() calls
                r"__proto__",  # Prototype pollution
                r"constructor\s*\[",  # Constructor access
                r"process\.env",  # Environment variable access
                r"require\s*\(",  # Node.js require
                r"import\s+",  # Import statements
                r"\.\.\/",  # Directory traversal
                r"\/etc\/passwd",  # Common target files
                r"cmd\.exe",  # Windows command
                r"powershell",  # PowerShell
                r"\x00",  # Null bytes
                r"union\s+select",  # SQL injection
                r"drop\s+table",  # SQL injection
                r"insert\s+into",  # SQL injection
                r"update\s+set",  # SQL injection
                r"delete\s+from",  # SQL injection
                r"';--",  # SQL comment injection
                r'";--',  # SQL comment injection
            ]


class InputSanitizer:
    """Sanitizes input data to prevent injection attacks."""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = ValidationConstants.MAX_NAME_LENGTH * 10) -> str:
        """Sanitize a string value."""
        if not isinstance(value, str):
            return str(value)
        
        # Truncate to max length
        value = value[:max_length]
        
        # HTML escape
        value = html.escape(value)
        
        # URL decode to catch encoded attacks
        try:
            value = urllib.parse.unquote(value)
        except Exception:
            pass
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Normalize whitespace
        value = ' '.join(value.split())
        
        return value
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any], config: ValidationConfig, depth: int = 0) -> Dict[str, Any]:
        """Recursively sanitize dictionary data."""
        if depth > config.max_nested_depth:
            raise ValueError(f"Maximum nesting depth ({config.max_nested_depth}) exceeded")
        
        sanitized = {}
        for key, value in data.items():
            # Sanitize key
            if not isinstance(key, str):
                continue
            
            sanitized_key = InputSanitizer.sanitize_string(key, config.max_field_length)
            
            # Sanitize value based on type
            if isinstance(value, str):
                sanitized[sanitized_key] = InputSanitizer.sanitize_string(value, config.max_field_length)
            elif isinstance(value, dict):
                sanitized[sanitized_key] = InputSanitizer.sanitize_dict(value, config, depth + 1)
            elif isinstance(value, list):
                sanitized[sanitized_key] = InputSanitizer.sanitize_list(value, config, depth + 1)
            elif isinstance(value, (int, float, bool, type(None))):
                sanitized[sanitized_key] = value
            else:
                # Convert other types to string and sanitize
                sanitized[sanitized_key] = InputSanitizer.sanitize_string(str(value), config.max_field_length)
        
        return sanitized
    
    @staticmethod
    def sanitize_list(data: List[Any], config: ValidationConfig, depth: int = 0) -> List[Any]:
        """Recursively sanitize list data."""
        if depth > config.max_nested_depth:
            raise ValueError(f"Maximum nesting depth ({config.max_nested_depth}) exceeded")
        
        if len(data) > config.max_array_length:
            logger.warning(f"Array truncated from {len(data)} to {config.max_array_length} items")
            data = data[:config.max_array_length]
        
        sanitized = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(InputSanitizer.sanitize_string(item, config.max_field_length))
            elif isinstance(item, dict):
                sanitized.append(InputSanitizer.sanitize_dict(item, config, depth + 1))
            elif isinstance(item, list):
                sanitized.append(InputSanitizer.sanitize_list(item, config, depth + 1))
            elif isinstance(item, (int, float, bool, type(None))):
                sanitized.append(item)
            else:
                sanitized.append(InputSanitizer.sanitize_string(str(item), config.max_field_length))
        
        return sanitized


class InputValidator:
    """Validates input data against security rules."""
    
    def __init__(self, config: ValidationConfig):
        self.config = config
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in config.blocked_patterns]
    
    def validate_string(self, value: str, field_name: str = "field") -> None:
        """Validate a string value against security rules."""
        # Check length
        if len(value) > self.config.max_field_length:
            raise ValueError(f"{field_name} exceeds maximum length of {self.config.max_field_length}")
        
        # Check for blocked patterns
        for pattern in self.compiled_patterns:
            if pattern.search(value):
                logger.warning(f"Blocked pattern detected in {field_name}: {pattern.pattern}")
                raise ValueError(f"Invalid content detected in {field_name}")
    
    def validate_dict(self, data: Dict[str, Any], depth: int = 0) -> None:
        """Recursively validate dictionary data."""
        if depth > self.config.max_nested_depth:
            raise ValueError(f"Maximum nesting depth ({self.config.max_nested_depth}) exceeded")
        
        for key, value in data.items():
            if isinstance(value, str):
                self.validate_string(value, f"field '{key}'")
            elif isinstance(value, dict):
                self.validate_dict(value, depth + 1)
            elif isinstance(value, list):
                self.validate_list(value, f"array '{key}'", depth + 1)
    
    def validate_list(self, data: List[Any], field_name: str = "array", depth: int = 0) -> None:
        """Recursively validate list data."""
        if depth > self.config.max_nested_depth:
            raise ValueError(f"Maximum nesting depth ({self.config.max_nested_depth}) exceeded")
        
        if len(data) > self.config.max_array_length:
            raise ValueError(f"{field_name} exceeds maximum length of {self.config.max_array_length}")
        
        for i, item in enumerate(data):
            if isinstance(item, str):
                self.validate_string(item, f"{field_name}[{i}]")
            elif isinstance(item, dict):
                self.validate_dict(item, depth + 1)
            elif isinstance(item, list):
                self.validate_list(item, f"{field_name}[{i}]", depth + 1)


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive input validation and sanitization.
    
    Features:
    - Content type validation
    - Input size limits
    - Pattern-based injection detection
    - Recursive sanitization
    - Detailed logging
    """
    
    def __init__(self, app, config: Optional[ValidationConfig] = None):
        super().__init__(app)
        self.config = config or ValidationConfig()
        self.validator = InputValidator(self.config)
        self.sanitizer = InputSanitizer()
        
        logger.info(f"Input validation middleware initialized with config: {self.config}")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through validation pipeline."""
        try:
            # Skip validation for certain paths
            if self._should_skip_validation(request):
                return await call_next(request)
            
            # Validate content type
            content_type = request.headers.get("content-type", "").split(";")[0].strip()
            if content_type and content_type not in self.config.allowed_content_types:
                logger.warning(f"Blocked request with content-type: {content_type}")
                raise HTTPException(status_code=415, detail="Unsupported content type")
            
            # Validate and sanitize based on content type
            if content_type == "application/json":
                await self._validate_json_request(request)
            elif content_type == "application/x-www-form-urlencoded":
                await self._validate_form_request(request)
            elif content_type == "multipart/form-data":
                await self._validate_multipart_request(request)
            
            # Validate headers
            self._validate_headers(request)
            
            # Validate query parameters
            self._validate_query_params(request)
            
            # Process request
            response = await call_next(request)
            return response
            
        except HTTPException:
            raise
        except ValueError as e:
            logger.warning(f"Input validation failed: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Input validation middleware error: {e}")
            raise HTTPException(status_code=500, detail="Internal validation error")
    
    def _should_skip_validation(self, request: Request) -> bool:
        """Check if validation should be skipped for this request."""
        # Skip for health checks and static files
        skip_paths = ["/health", "/healthz", "/docs", "/openapi.json", "/favicon.ico"]
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    async def _validate_json_request(self, request: Request) -> None:
        """Validate and sanitize JSON request body."""
        try:
            # Read body
            body = await request.body()
            
            # Check size
            if len(body) > self.config.max_input_length:
                raise ValueError(f"Request body exceeds maximum size of {self.config.max_input_length} bytes")
            
            # Parse JSON
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON in request body")
            
            # Validate structure
            if isinstance(data, dict):
                self.validator.validate_dict(data)
                # Sanitize and store for handler use
                sanitized = self.sanitizer.sanitize_dict(data, self.config)
                request.state.sanitized_body = sanitized
            elif isinstance(data, list):
                self.validator.validate_list(data)
                sanitized = self.sanitizer.sanitize_list(data, self.config)
                request.state.sanitized_body = sanitized
            else:
                raise ValueError("Request body must be an object or array")
                
        except Exception as e:
            logger.error(f"JSON validation error: {e}")
            raise
    
    async def _validate_form_request(self, request: Request) -> None:
        """Validate and sanitize form data."""
        try:
            form_data = await request.form()
            
            # Convert to dict and validate
            data = {}
            for key, value in form_data.items():
                if isinstance(value, str):
                    self.validator.validate_string(value, key)
                    data[key] = self.sanitizer.sanitize_string(value, self.config.max_field_length)
                else:
                    data[key] = value
            
            request.state.sanitized_form = data
            
        except Exception as e:
            logger.error(f"Form validation error: {e}")
            raise
    
    async def _validate_multipart_request(self, request: Request) -> None:
        """Validate multipart form data."""
        # For now, delegate to form validation
        # Could be extended for file upload validation
        await self._validate_form_request(request)
    
    def _validate_headers(self, request: Request) -> None:
        """Validate request headers."""
        dangerous_headers = ["x-forwarded-for", "x-real-ip", "x-forwarded-host"]
        
        for header_name, header_value in request.headers.items():
            # Check header value length
            if len(header_value) > self.config.max_field_length:
                logger.warning(f"Header {header_name} exceeds maximum length")
                raise ValueError(f"Header {header_name} too long")
            
            # Validate dangerous headers more strictly
            if header_name.lower() in dangerous_headers:
                try:
                    self.validator.validate_string(header_value, f"header '{header_name}'")
                except ValueError:
                    logger.warning(f"Dangerous content in header {header_name}")
                    # Don't expose which header failed for security
                    raise ValueError("Invalid header content")
    
    def _validate_query_params(self, request: Request) -> None:
        """Validate query parameters."""
        for param_name, param_value in request.query_params.items():
            if isinstance(param_value, str):
                self.validator.validate_string(param_value, f"query parameter '{param_name}'")
            
            # Store sanitized version
            if not hasattr(request.state, "sanitized_query"):
                request.state.sanitized_query = {}
            
            request.state.sanitized_query[param_name] = self.sanitizer.sanitize_string(
                param_value, self.config.max_field_length
            )


# Pydantic models for common validation scenarios
class ConversationMessageInput(BaseModel):
    """Validated conversation message input."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=5000)
    timestamp: Optional[str] = None
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        # Additional content validation
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class CustomerProfileInput(BaseModel):
    """Validated customer profile input."""
    id: Optional[str] = Field(None, max_length=ValidationConstants.MAX_NAME_LENGTH)
    name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    phone: Optional[str] = Field(None, pattern=r"^\+?[\d\s\-\(\)]+$")
    business_type: Optional[str] = Field(None, max_length=ValidationConstants.MAX_NAME_LENGTH)
    
    @field_validator('name', 'business_type')
    @classmethod
    def validate_text_fields(cls, v):
        if v and not re.match(r"^[\w\s\-\.]+$", v):
            raise ValueError("Invalid characters in text field")
        return v


def create_input_validation_middleware(config: Optional[ValidationConfig] = None) -> InputValidationMiddleware:
    """Factory function to create input validation middleware."""
    return lambda app: InputValidationMiddleware(app, config)