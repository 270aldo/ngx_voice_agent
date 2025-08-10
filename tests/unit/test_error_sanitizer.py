"""
Unit tests for error sanitizer functionality.
"""

import pytest
from src.utils.error_sanitizer import (
    ErrorSanitizer,
    ErrorSeverity,
    sanitize_error,
    safe_error_response
)


class TestErrorSanitizer:
    """Test error sanitizer functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sanitizer = ErrorSanitizer(log_full_errors=False)
    
    def test_sanitize_file_paths(self):
        """Test that file paths are sanitized."""
        # Test various file path formats
        test_cases = [
            ("/Users/johndoe/project/file.py", "/Users/***/project/file.py"),
            ("/home/ubuntu/app/secret.py", "/home/***/app/secret.py"),
            ("C:\\Users\\Admin\\Desktop\\app.py", "C:\\Users\\***\\Desktop\\app.py"),
            ("/var/www/myapp/config.py", "/var/www/***/config.py"),
        ]
        
        for original, expected in test_cases:
            error = Exception(f"Error in file {original}")
            sanitized = self.sanitizer.sanitize_error(error)
            assert expected in sanitized.message
            assert original not in sanitized.message
    
    def test_sanitize_credentials(self):
        """Test that credentials are sanitized."""
        # Test API keys
        error = Exception("Invalid API key: sk-1234567890abcdef1234567890abcdef12345678")
        sanitized = self.sanitizer.sanitize_error(error)
        assert "sk-***" in sanitized.message
        assert "sk-1234567890" not in sanitized.message
        
        # Test passwords
        error = Exception("Authentication failed with password='mysecretpass123'")
        sanitized = self.sanitizer.sanitize_error(error)
        assert "password=***" in sanitized.message
        assert "mysecretpass123" not in sanitized.message
        
        # Test database URLs
        error = Exception("Cannot connect to postgresql://user:pass@localhost:5432/db")
        sanitized = self.sanitizer.sanitize_error(error)
        assert "postgresql://***:***@***" in sanitized.message
        assert "user:pass" not in sanitized.message
    
    def test_sanitize_sensitive_data(self):
        """Test sanitization of various sensitive data."""
        # Email addresses
        error = Exception("User john.doe@example.com not found")
        sanitized = self.sanitizer.sanitize_error(error)
        assert "***@***.***" in sanitized.message
        assert "john.doe@example.com" not in sanitized.message
        
        # IP addresses
        error = Exception("Connection refused from 192.168.1.100")
        sanitized = self.sanitizer.sanitize_error(error)
        assert "***.***.***.***" in sanitized.message
        assert "192.168.1.100" not in sanitized.message
        
        # UUIDs
        error = Exception("Session 550e8400-e29b-41d4-a716-446655440000 expired")
        sanitized = self.sanitizer.sanitize_error(error)
        assert "***-***-***-***-***" in sanitized.message
        assert "550e8400" not in sanitized.message
    
    def test_error_code_mapping(self):
        """Test that error types are mapped to appropriate codes."""
        # Database errors
        from unittest.mock import Mock
        
        # Create mock exceptions with proper type names
        integrity_error = type('IntegrityError', (Exception,), {})()
        sanitized = self.sanitizer.sanitize_error(integrity_error)
        assert sanitized.error_code == "DB_INTEGRITY_ERROR"
        
        # Validation errors
        validation_error = type('ValidationError', (Exception,), {})()
        sanitized = self.sanitizer.sanitize_error(validation_error)
        assert sanitized.error_code == "VALIDATION_ERROR"
        
        # Unknown errors
        unknown_error = Exception("Some error")
        sanitized = self.sanitizer.sanitize_error(unknown_error)
        assert sanitized.error_code == "UNKNOWN_ERROR"
    
    def test_error_severity(self):
        """Test error severity classification."""
        # Critical errors
        memory_error = MemoryError("Out of memory")
        sanitized = self.sanitizer.sanitize_error(memory_error)
        assert sanitized.severity == ErrorSeverity.CRITICAL
        
        # High severity
        auth_error = type('AuthenticationError', (Exception,), {})()
        sanitized = self.sanitizer.sanitize_error(auth_error)
        assert sanitized.severity == ErrorSeverity.HIGH
        
        # Medium severity
        value_error = ValueError("Invalid value")
        sanitized = self.sanitizer.sanitize_error(value_error)
        assert sanitized.severity == ErrorSeverity.MEDIUM
        
        # Low severity
        generic_error = Exception("Generic error")
        sanitized = self.sanitizer.sanitize_error(generic_error)
        assert sanitized.severity == ErrorSeverity.LOW
    
    def test_user_friendly_messages(self):
        """Test that user-friendly messages are provided."""
        # Database connection error
        db_error = type('OperationalError', (Exception,), {})()
        sanitized = self.sanitizer.sanitize_error(db_error)
        assert sanitized.user_message == "We're having trouble connecting to our database. Please try again in a moment."
        
        # Validation error
        val_error = type('ValidationError', (Exception,), {})()
        sanitized = self.sanitizer.sanitize_error(val_error)
        assert sanitized.user_message == "The provided data is invalid. Please check your input."
        
        # Unknown error
        unknown = Exception("Something went wrong")
        sanitized = self.sanitizer.sanitize_error(unknown)
        assert sanitized.user_message == "An unexpected error occurred. Please try again or contact support."
    
    def test_stack_trace_sanitization(self):
        """Test stack trace sanitization."""
        stack_trace = """
Traceback (most recent call last):
  File "/Users/johndoe/project/app.py", line 42, in process
    connect_to_db("postgresql://admin:secret123@localhost:5432/mydb")
  File "/home/ubuntu/lib/db.py", line 10, in connect
    raise ConnectionError("Failed with api_key=sk-1234567890abcdef")
ConnectionError: Failed with api_key=sk-1234567890abcdef
        """
        
        sanitized_trace = self.sanitizer.sanitize_stack_trace(stack_trace)
        
        # Check file paths are sanitized
        assert "/Users/johndoe" not in sanitized_trace
        assert "app.py" in sanitized_trace  # Filename should remain
        
        # Check credentials are sanitized
        assert "admin:secret123" not in sanitized_trace
        assert "postgresql://***:***@***" in sanitized_trace
        assert "sk-1234567890abcdef" not in sanitized_trace
        assert "api_key=***" in sanitized_trace
    
    def test_message_truncation(self):
        """Test that long messages are truncated."""
        long_message = "Error: " + "x" * 1000
        error = Exception(long_message)
        sanitized = self.sanitizer.sanitize_error(error)
        
        assert len(sanitized.message) == 500
        assert sanitized.message.endswith("...")
    
    def test_request_id_handling(self):
        """Test request ID is included in sanitized error."""
        error = Exception("Test error")
        request_id = "req-12345"
        
        sanitized = self.sanitizer.sanitize_error(error, request_id=request_id)
        
        assert sanitized.request_id == request_id
        assert sanitized.timestamp is not None
    
    def test_safe_error_response(self):
        """Test safe error response helper."""
        error = ValueError("Invalid input")
        response = safe_error_response(error, status_code=400, request_id="req-123")
        
        assert response["error"] is True
        assert response["status_code"] == 400
        assert response["error_code"] == "INVALID_VALUE_ERROR"
        assert response["message"] == "One or more values are invalid. Please review your input."
        assert response["request_id"] == "req-123"
        assert response["timestamp"] is not None
    
    def test_context_handling(self):
        """Test that context is properly handled."""
        error = Exception("Test error")
        context = {
            "user_id": 123,
            "action": "create_order",
            "sensitive_data": "password=secret123"
        }
        
        # Context should be logged but not exposed
        sanitized = self.sanitizer.sanitize_error(error, context=context)
        
        # Sanitized error should not contain context
        error_dict = sanitized.to_dict()
        assert "context" not in error_dict
        assert "user_id" not in str(error_dict)
        assert "sensitive_data" not in str(error_dict)


class TestErrorSanitizerIntegration:
    """Test error sanitizer integration scenarios."""
    
    def test_complex_error_message(self):
        """Test sanitization of complex error messages."""
        error_msg = """
        Database connection failed:
        - Host: 192.168.1.100:5432
        - User: admin@company.com
        - Password: supersecret123
        - Database: /Users/admin/data/production.db
        - API Key: sk-proj-1234567890abcdef1234567890abcdef12345678
        """
        
        error = Exception(error_msg)
        sanitized = sanitize_error(error)
        
        # Verify all sensitive data is sanitized
        assert "192.168.1.100" not in sanitized.message
        assert "admin@company.com" not in sanitized.message
        assert "supersecret123" not in sanitized.message
        assert "/Users/admin" not in sanitized.message
        assert "sk-proj-1234567890" not in sanitized.message
        
        # Verify replacements are present
        assert "***.***.***.***" in sanitized.message
        assert "***@***.***" in sanitized.message
        assert "Password: ***" in sanitized.message
        assert "/Users/***" in sanitized.message
        assert "sk-***" in sanitized.message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])