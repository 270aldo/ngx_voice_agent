"""
Input sanitization utilities for XSS prevention.

This module provides comprehensive sanitization functions to prevent
Cross-Site Scripting (XSS) attacks by cleaning user inputs.
"""

import re
import html
import json
from typing import Any, Dict, List, Union, Optional
from urllib.parse import urlparse, quote
import bleach
from markupsafe import Markup, escape

# Allowed HTML tags for rich text content (if needed)
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'i', 'b',
    'ul', 'ol', 'li', 'blockquote', 'code', 'pre'
]

# Allowed HTML attributes
ALLOWED_ATTRIBUTES = {
    '*': ['class'],
    'code': ['class', 'data-language']
}

# Dangerous patterns to remove
DANGEROUS_PATTERNS = [
    # JavaScript events
    re.compile(r'on\w+\s*=', re.IGNORECASE),
    # JavaScript protocol
    re.compile(r'javascript\s*:', re.IGNORECASE),
    # VBScript protocol
    re.compile(r'vbscript\s*:', re.IGNORECASE),
    # Data URI with script
    re.compile(r'data\s*:.*script', re.IGNORECASE),
    # Meta refresh
    re.compile(r'<\s*meta[^>]+refresh', re.IGNORECASE),
    # Import statements
    re.compile(r'@import', re.IGNORECASE),
    # Expression CSS
    re.compile(r'expression\s*\(', re.IGNORECASE)
]

# SQL injection patterns (basic)
SQL_PATTERNS = [
    # SQL keywords with suspicious context (not just the word alone)
    re.compile(r'(union\s+select|select\s+\*|insert\s+into|update\s+\w+\s+set|delete\s+from|drop\s+(table|database)|create\s+(table|database)|alter\s+table|exec\s+\w+|execute\s+\w+)', re.IGNORECASE),
    re.compile(r'(--|#|/\*|\*/)', re.IGNORECASE),
    re.compile(r"(';|';|;|'=|'=)", re.IGNORECASE)
]


class InputSanitizer:
    """Main class for input sanitization."""
    
    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize plain text input by escaping HTML entities.
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text safe for HTML context
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Trim to max length if specified
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        # HTML escape
        sanitized = html.escape(text, quote=True)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Remove non-printable characters (except newlines and tabs)
        sanitized = ''.join(char for char in sanitized 
                          if char.isprintable() or char in '\n\r\t')
        
        return sanitized
    
    @staticmethod
    def sanitize_html(html_content: str, allowed_tags: List[str] = None, 
                     allowed_attributes: Dict[str, List[str]] = None) -> str:
        """
        Sanitize HTML content allowing only safe tags and attributes.
        
        Args:
            html_content: HTML content to sanitize
            allowed_tags: List of allowed HTML tags
            allowed_attributes: Dict of allowed attributes per tag
            
        Returns:
            Sanitized HTML safe for rendering
        """
        if not html_content:
            return ""
        
        # Use default allowed tags/attributes if not specified
        tags = allowed_tags or ALLOWED_TAGS
        attrs = allowed_attributes or ALLOWED_ATTRIBUTES
        
        # Clean with bleach
        cleaned = bleach.clean(
            html_content,
            tags=tags,
            attributes=attrs,
            strip=True,
            strip_comments=True
        )
        
        # Additional cleaning for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            cleaned = pattern.sub('', cleaned)
        
        return cleaned
    
    @staticmethod
    def sanitize_json(data: Union[Dict, List, str], max_depth: int = 10) -> Union[Dict, List, str]:
        """
        Recursively sanitize JSON data structures.
        
        Args:
            data: JSON data to sanitize
            max_depth: Maximum recursion depth
            
        Returns:
            Sanitized JSON data
        """
        if max_depth <= 0:
            return None
        
        if isinstance(data, dict):
            return {
                InputSanitizer.sanitize_text(k): InputSanitizer.sanitize_json(v, max_depth - 1)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [InputSanitizer.sanitize_json(item, max_depth - 1) for item in data]
        elif isinstance(data, str):
            return InputSanitizer.sanitize_text(data)
        else:
            return data
    
    @staticmethod
    def sanitize_url(url: str) -> Optional[str]:
        """
        Sanitize URL to prevent XSS through URLs.
        
        Args:
            url: URL to sanitize
            
        Returns:
            Sanitized URL or None if invalid
        """
        if not url:
            return None
        
        try:
            # Parse URL
            parsed = urlparse(url)
            
            # Allow only http(s) and relative URLs
            if parsed.scheme and parsed.scheme not in ['http', 'https']:
                return None
            
            # Check for dangerous patterns
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in ['javascript:', 'vbscript:', 'data:']):
                return None
            
            # Reconstruct URL with proper encoding
            if parsed.scheme:
                return url  # Full URL seems safe
            else:
                # Relative URL - encode it
                return quote(url, safe='/:?&=')
                
        except Exception:
            return None
    
    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 255) -> str:
        """
        Sanitize filename to prevent path traversal and other attacks.
        
        Args:
            filename: Filename to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized filename
        """
        if not filename:
            return "unnamed"
        
        # Replace path traversal patterns and separators with underscore
        filename = filename.replace('../', '_').replace('..\\', '_')
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove null bytes
        filename = filename.replace('\x00', '')
        
        # Replace spaces with underscore
        filename = filename.replace(' ', '_')
        
        # Allow only alphanumeric, dash, underscore, and dot
        filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        
        # Ensure it doesn't start with a dot (hidden file)
        if filename.startswith('.'):
            filename = '_' + filename[1:]
        
        # Trim to max length
        if len(filename) > max_length:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            if ext:
                name = name[:max_length - len(ext) - 1]
                filename = f"{name}.{ext}"
            else:
                filename = filename[:max_length]
        
        return filename or "unnamed"
    
    @staticmethod
    def sanitize_sql_identifier(identifier: str) -> str:
        """
        Sanitize SQL identifiers (table names, column names).
        
        Args:
            identifier: SQL identifier to sanitize
            
        Returns:
            Sanitized identifier
        """
        # Allow only alphanumeric and underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', identifier)
        
        # Ensure it starts with a letter or underscore
        if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
            sanitized = '_' + sanitized
        
        # Limit length
        return sanitized[:63]  # PostgreSQL identifier limit
    
    @staticmethod
    def detect_sql_injection(text: str) -> bool:
        """
        Detect potential SQL injection attempts.
        
        Args:
            text: Text to check
            
        Returns:
            True if SQL injection pattern detected
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check for SQL patterns
        for pattern in SQL_PATTERNS:
            if pattern.search(text_lower):
                return True
        
        # Check for common SQL injection techniques
        suspicious = [
            '1=1', '1 = 1',
            'or 1=1', 'or 1 = 1',
            '\' or \'', '" or "',
            'admin\'--', 'admin"--'
        ]
        
        return any(s in text_lower for s in suspicious)
    
    @staticmethod
    def sanitize_email(email: str) -> Optional[str]:
        """
        Sanitize and validate email address.
        
        Args:
            email: Email address to sanitize
            
        Returns:
            Sanitized email or None if invalid
        """
        if not email:
            return None
        
        # Basic email regex
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        # Trim and lowercase
        email = email.strip().lower()
        
        # Check pattern
        if email_pattern.match(email):
            return email
        
        return None
    
    @staticmethod
    def sanitize_phone(phone: str) -> Optional[str]:
        """
        Sanitize phone number.
        
        Args:
            phone: Phone number to sanitize
            
        Returns:
            Sanitized phone number
        """
        if not phone:
            return None
        
        # Keep only digits, +, -, (, ), and spaces
        sanitized = re.sub(r'[^0-9+\-() ]', '', phone)
        
        # Remove multiple spaces
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Basic length check
        if len(sanitized) < 7 or len(sanitized) > 20:
            return None
        
        return sanitized


def sanitize_request_data(data: Any, sanitize_html_content: bool = False) -> Any:
    """
    Sanitize all string values in request data recursively.
    
    Args:
        data: Request data to sanitize
        sanitize_html_content: Whether to allow HTML tags
        
    Returns:
        Sanitized data
    """
    sanitizer = InputSanitizer()
    
    def _sanitize_recursive(value: Any, depth: int = 0) -> Any:
        if depth > 10:  # Prevent infinite recursion
            return None
            
        if isinstance(value, dict):
            return {
                k: _sanitize_recursive(v, depth + 1)
                for k, v in value.items()
            }
        elif isinstance(value, list):
            return [_sanitize_recursive(item, depth + 1) for item in value]
        elif isinstance(value, str):
            if sanitize_html_content:
                return sanitizer.sanitize_html(value)
            else:
                return sanitizer.sanitize_text(value)
        else:
            return value
    
    return _sanitize_recursive(data)


def create_safe_markdown(text: str) -> str:
    """
    Create safe markdown by escaping dangerous patterns.
    
    Args:
        text: Markdown text
        
    Returns:
        Safe markdown
    """
    if not text:
        return ""
    
    # Escape HTML first
    text = html.escape(text)
    
    # Allow basic markdown but escape dangerous patterns
    # This is a simplified version - use a proper markdown parser for production
    safe_patterns = {
        r'\*\*(.*?)\*\*': r'<strong>\1</strong>',  # Bold
        r'\*(.*?)\*': r'<em>\1</em>',  # Italic
        r'`(.*?)`': r'<code>\1</code>',  # Inline code
    }
    
    for pattern, replacement in safe_patterns.items():
        text = re.sub(pattern, replacement, text)
    
    return text