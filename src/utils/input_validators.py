"""
Input validators for critical data models.

This module provides specialized validators for different types of inputs
to ensure data integrity and prevent injection attacks.
"""

import re
from typing import Optional, Dict, Any, List
from pydantic import validator, BaseModel
from email_validator import validate_email, EmailNotValidError

from src.utils.sanitization import InputSanitizer
from src.core.constants import ValidationConstants


class ConversationInputValidator:
    """Validators for conversation-related inputs."""
    
    @staticmethod
    def validate_message_content(content: str) -> str:
        """
        Validate and sanitize message content.
        
        Args:
            content: Message content to validate
            
        Returns:
            Sanitized content
            
        Raises:
            ValueError: If content is invalid
        """
        if not content:
            raise ValueError("Message content cannot be empty")
        
        # Check length
        if len(content) > ValidationConstants.MAX_MESSAGE_LENGTH:  # Character limit
            raise ValueError(f"Message content exceeds maximum length of {ValidationConstants.MAX_MESSAGE_LENGTH}")
        
        # Sanitize
        sanitizer = InputSanitizer()
        sanitized = sanitizer.sanitize_text(content)
        
        # Check for SQL injection attempts
        if sanitizer.detect_sql_injection(content):
            raise ValueError("Message contains potentially dangerous content")
        
        return sanitized
    
    @staticmethod
    def validate_conversation_id(conv_id: str) -> str:
        """Validate conversation ID format."""
        # Expected format: UUID or custom format like "conv-123"
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        custom_pattern = re.compile(r'^conv-[a-zA-Z0-9]{1,50}$')
        
        if not (uuid_pattern.match(conv_id) or custom_pattern.match(conv_id)):
            raise ValueError("Invalid conversation ID format")
        
        return conv_id


class CustomerDataValidator:
    """Validators for customer data inputs."""
    
    @staticmethod
    def validate_customer_name(name: str) -> str:
        """
        Validate and sanitize customer name.
        
        Args:
            name: Customer name to validate
            
        Returns:
            Sanitized name
            
        Raises:
            ValueError: If name is invalid
        """
        if not name:
            raise ValueError("Customer name is required")
        
        # Basic length check
        if len(name) < ValidationConstants.MIN_NAME_LENGTH or len(name) > ValidationConstants.MAX_NAME_LENGTH:
            raise ValueError(f"Name must be between {ValidationConstants.MIN_NAME_LENGTH} and {ValidationConstants.MAX_NAME_LENGTH} characters")
        
        # Allow letters, spaces, hyphens, apostrophes
        name_pattern = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s\-'\.]+$")
        if not name_pattern.match(name):
            raise ValueError("Name contains invalid characters")
        
        # Sanitize
        sanitizer = InputSanitizer()
        return sanitizer.sanitize_text(name)
    
    @staticmethod
    def validate_customer_email(email: str) -> str:
        """
        Validate and sanitize email address.
        
        Args:
            email: Email to validate
            
        Returns:
            Sanitized email
            
        Raises:
            ValueError: If email is invalid
        """
        if not email:
            raise ValueError("Email is required")
        
        try:
            # Use email-validator library
            validation = validate_email(email, check_deliverability=False)
            return validation.email.lower()
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email: {str(e)}")
    
    @staticmethod
    def validate_customer_phone(phone: str) -> str:
        """
        Validate and sanitize phone number.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            Sanitized phone
            
        Raises:
            ValueError: If phone is invalid
        """
        if not phone:
            return ""  # Phone is optional
        
        sanitizer = InputSanitizer()
        sanitized = sanitizer.sanitize_phone(phone)
        
        if not sanitized:
            raise ValueError("Invalid phone number format")
        
        return sanitized
    
    @staticmethod
    def validate_age(age: Any) -> int:
        """
        Validate age input.
        
        Args:
            age: Age to validate
            
        Returns:
            Valid age
            
        Raises:
            ValueError: If age is invalid
        """
        try:
            age_int = int(age)
        except (ValueError, TypeError):
            raise ValueError("Age must be a number")
        
        if age_int < ValidationConstants.MIN_AGE or age_int > ValidationConstants.MAX_AGE:
            raise ValueError(f"Age must be between {ValidationConstants.MIN_AGE} and {ValidationConstants.MAX_AGE}")
        
        return age_int
    
    @staticmethod
    def validate_occupation(occupation: str) -> str:
        """
        Validate and sanitize occupation.
        
        Args:
            occupation: Occupation to validate
            
        Returns:
            Sanitized occupation
            
        Raises:
            ValueError: If occupation is invalid
        """
        if not occupation:
            return ""  # Optional field
        
        if len(occupation) > ValidationConstants.MAX_NAME_LENGTH:
            raise ValueError("Occupation exceeds maximum length")
        
        # Allow letters, numbers, spaces, common punctuation
        occupation_pattern = re.compile(r"^[a-zA-Z0-9\s\-/&,\.]+$")
        if not occupation_pattern.match(occupation):
            raise ValueError("Occupation contains invalid characters")
        
        sanitizer = InputSanitizer()
        return sanitizer.sanitize_text(occupation)


class SearchQueryValidator:
    """Validators for search queries."""
    
    @staticmethod
    def validate_search_query(query: str, max_length: int = 200) -> str:
        """
        Validate and sanitize search query.
        
        Args:
            query: Search query to validate
            max_length: Maximum allowed length
            
        Returns:
            Sanitized query
            
        Raises:
            ValueError: If query is invalid
        """
        if not query:
            raise ValueError("Search query cannot be empty")
        
        if len(query) > max_length:
            raise ValueError(f"Search query exceeds maximum length of {max_length}")
        
        # Remove potentially dangerous characters for search
        # Allow letters, numbers, spaces, and basic punctuation
        cleaned = re.sub(r'[^\w\s\-\.\,\?\!áéíóúÁÉÍÓÚñÑ]', ' ', query)
        
        # Remove multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        if not cleaned:
            raise ValueError("Search query contains no valid characters")
        
        return cleaned
    
    @staticmethod
    def validate_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate search filters.
        
        Args:
            filters: Dictionary of filters
            
        Returns:
            Validated filters
            
        Raises:
            ValueError: If filters are invalid
        """
        allowed_filters = {
            'tier', 'status', 'date_from', 'date_to', 
            'min_score', 'max_score', 'tags'
        }
        
        validated = {}
        
        for key, value in filters.items():
            if key not in allowed_filters:
                continue  # Skip unknown filters
            
            if key in ['tier', 'status']:
                # Enum-like fields
                if not isinstance(value, str) or len(value) > 50:
                    raise ValueError(f"Invalid {key} filter")
                validated[key] = value.upper()
                
            elif key in ['date_from', 'date_to']:
                # Date fields - validate ISO format
                date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?')
                if not date_pattern.match(str(value)):
                    raise ValueError(f"Invalid date format for {key}")
                validated[key] = value
                
            elif key in ['min_score', 'max_score']:
                # Numeric fields
                try:
                    score = float(value)
                    if score < 0 or score > 1:
                        raise ValueError(f"{key} must be between 0 and 1")
                    validated[key] = score
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid {key} value")
                    
            elif key == 'tags':
                # List field
                if isinstance(value, list):
                    validated[key] = [str(tag)[:50] for tag in value[:10]]  # Limit tags
                else:
                    raise ValueError("Tags must be a list")
        
        return validated


class FileUploadValidator:
    """Validators for file uploads."""
    
    ALLOWED_EXTENSIONS = {
        'image': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
        'document': ['pdf', 'doc', 'docx', 'txt'],
        'audio': ['mp3', 'wav', 'ogg', 'm4a']
    }
    
    MAX_FILE_SIZES = {
        'image': ValidationConstants.MAX_FILE_SIZE_MB * 1024 * 1024,      # 10 MB
        'document': ValidationConstants.MAX_FILE_SIZE_MB * 5 * 1024 * 1024,   # 50 MB
        'audio': ValidationConstants.MAX_FILE_SIZE_MB * 10 * 1024 * 1024      # 100 MB
    }
    
    @classmethod
    def validate_filename(cls, filename: str, file_type: str = 'document') -> str:
        """
        Validate and sanitize filename.
        
        Args:
            filename: Original filename
            file_type: Type of file (image, document, audio)
            
        Returns:
            Sanitized filename
            
        Raises:
            ValueError: If filename is invalid
        """
        if not filename:
            raise ValueError("Filename is required")
        
        sanitizer = InputSanitizer()
        sanitized = sanitizer.sanitize_filename(filename)
        
        # Check extension
        if '.' in sanitized:
            ext = sanitized.rsplit('.', 1)[1].lower()
            allowed = cls.ALLOWED_EXTENSIONS.get(file_type, [])
            if ext not in allowed:
                raise ValueError(f"File type .{ext} is not allowed")
        else:
            raise ValueError("File must have an extension")
        
        return sanitized
    
    @classmethod
    def validate_file_size(cls, size: int, file_type: str = 'document') -> None:
        """
        Validate file size.
        
        Args:
            size: File size in bytes
            file_type: Type of file
            
        Raises:
            ValueError: If file size exceeds limit
        """
        max_size = cls.MAX_FILE_SIZES.get(file_type, ValidationConstants.MAX_FILE_SIZE_MB * 1024 * 1024)
        
        if size > max_size:
            max_mb = max_size / (1024 * 1024)
            raise ValueError(f"File size exceeds maximum of {max_mb}MB")
    
    @staticmethod
    def validate_mime_type(mime_type: str, expected_types: List[str]) -> None:
        """
        Validate MIME type.
        
        Args:
            mime_type: Actual MIME type
            expected_types: List of expected MIME types
            
        Raises:
            ValueError: If MIME type doesn't match
        """
        if mime_type not in expected_types:
            raise ValueError(f"Invalid file type: {mime_type}")


# Pydantic validators for models
def create_validators_for_model(model_class: BaseModel):
    """
    Create validators for a Pydantic model.
    
    This function can be used as a decorator to add validators to models.
    """
    
    # Add message content validator
    if hasattr(model_class, 'content'):
        model_class.validate_content = validator('content', allow_reuse=True)(
            ConversationInputValidator.validate_message_content
        )
    
    # Add email validator
    if hasattr(model_class, 'email'):
        model_class.validate_email = validator('email', allow_reuse=True)(
            CustomerDataValidator.validate_customer_email
        )
    
    # Add name validator
    if hasattr(model_class, 'name'):
        model_class.validate_name = validator('name', allow_reuse=True)(
            CustomerDataValidator.validate_customer_name
        )
    
    # Add phone validator
    if hasattr(model_class, 'phone'):
        model_class.validate_phone = validator('phone', allow_reuse=True)(
            CustomerDataValidator.validate_customer_phone
        )
    
    return model_class