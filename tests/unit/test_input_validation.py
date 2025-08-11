"""
Unit tests for input validation middleware.
"""

import pytest
import json
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from src.api.middleware.input_validation import (
    InputValidationMiddleware,
    ValidationConfig,
    InputSanitizer,
    InputValidator,
    ConversationMessageInput,
    CustomerProfileInput
)


def test_input_sanitizer():
    """Test input sanitization functionality."""
    sanitizer = InputSanitizer()
    
    # Test string sanitization
    assert sanitizer.sanitize_string("<script>alert('xss')</script>") == "&lt;script&gt;alert('xss')&lt;/script&gt;"
    assert sanitizer.sanitize_string("normal text") == "normal text"
    assert sanitizer.sanitize_string("text\x00with\x00nulls") == "textwithulls"
    
    # Test dictionary sanitization
    config = ValidationConfig()
    data = {
        "name": "<b>John</b>",
        "script": "<script>alert(1)</script>",
        "nested": {
            "value": "safe"
        }
    }
    
    sanitized = sanitizer.sanitize_dict(data, config)
    assert sanitized["name"] == "&lt;b&gt;John&lt;/b&gt;"
    assert sanitized["script"] == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert sanitized["nested"]["value"] == "safe"


def test_input_validator():
    """Test input validation functionality."""
    config = ValidationConfig()
    validator = InputValidator(config)
    
    # Test string validation
    validator.validate_string("safe string")  # Should not raise
    
    with pytest.raises(ValueError, match="Invalid content detected"):
        validator.validate_string("<script>alert('xss')</script>")
    
    with pytest.raises(ValueError, match="Invalid content detected"):
        validator.validate_string("javascript:alert(1)")
    
    with pytest.raises(ValueError, match="Invalid content detected"):
        validator.validate_string("'; DROP TABLE users; --")
    
    # Test length validation
    with pytest.raises(ValueError, match="exceeds maximum length"):
        validator.validate_string("x" * 10000)


def test_validation_config():
    """Test validation configuration."""
    config = ValidationConfig()
    
    assert config.max_input_length == 10000
    assert config.max_field_length == 1000
    assert config.max_array_length == 100
    assert config.max_nested_depth == 5
    assert "application/json" in config.allowed_content_types


def test_conversation_message_input():
    """Test conversation message input validation."""
    # Valid input
    msg = ConversationMessageInput(
        role="user",
        content="Hello, how can I help?"
    )
    assert msg.role == "user"
    assert msg.content == "Hello, how can I help?"
    
    # Invalid role
    with pytest.raises(ValueError):
        ConversationMessageInput(
            role="invalid",
            content="test"
        )
    
    # Empty content
    with pytest.raises(ValueError):
        ConversationMessageInput(
            role="user",
            content="   "
        )


def test_customer_profile_input():
    """Test customer profile input validation."""
    # Valid input
    profile = CustomerProfileInput(
        name="John Doe",
        email="john@example.com",
        phone="+1234567890",
        business_type="Gym"
    )
    assert profile.name == "John Doe"
    assert profile.email == "john@example.com"
    
    # Invalid email
    with pytest.raises(ValueError):
        CustomerProfileInput(
            email="not-an-email"
        )
    
    # Invalid phone
    with pytest.raises(ValueError):
        CustomerProfileInput(
            phone="phone123abc"
        )
    
    # Invalid name characters
    with pytest.raises(ValueError):
        CustomerProfileInput(
            name="John<script>"
        )


@pytest.mark.asyncio
async def test_input_validation_middleware():
    """Test input validation middleware integration."""
    app = FastAPI()
    
    # Add middleware
    config = ValidationConfig()
    app.add_middleware(InputValidationMiddleware, config=config)
    
    # Add test endpoint
    @app.post("/test")
    async def test_endpoint(request: Request):
        # Access sanitized body if available
        if hasattr(request.state, "sanitized_body"):
            return {"sanitized": request.state.sanitized_body}
        return {"message": "ok"}
    
    client = TestClient(app)
    
    # Test valid JSON
    response = client.post(
        "/test",
        json={"message": "hello"},
        headers={"content-type": "application/json"}
    )
    assert response.status_code == 200
    
    # Test XSS attempt
    response = client.post(
        "/test",
        json={"message": "<script>alert('xss')</script>"},
        headers={"content-type": "application/json"}
    )
    assert response.status_code == 400  # Should be blocked
    
    # Test SQL injection attempt
    response = client.post(
        "/test",
        json={"query": "'; DROP TABLE users; --"},
        headers={"content-type": "application/json"}
    )
    assert response.status_code == 400  # Should be blocked
    
    # Test oversized input
    large_data = {"data": "x" * 20000}
    response = client.post(
        "/test",
        json=large_data,
        headers={"content-type": "application/json"}
    )
    assert response.status_code == 400  # Should be blocked
    
    # Test invalid content type
    response = client.post(
        "/test",
        data="test",
        headers={"content-type": "text/plain"}
    )
    assert response.status_code == 415  # Unsupported media type


@pytest.mark.asyncio
async def test_nested_validation():
    """Test nested data structure validation."""
    config = ValidationConfig(max_nested_depth=2)
    validator = InputValidator(config)
    
    # Valid nested data
    data = {
        "level1": {
            "level2": {
                "value": "ok"
            }
        }
    }
    validator.validate_dict(data)  # Should not raise
    
    # Too deeply nested
    data = {
        "level1": {
            "level2": {
                "level3": {
                    "value": "too deep"
                }
            }
        }
    }
    with pytest.raises(ValueError, match="Maximum nesting depth"):
        validator.validate_dict(data)


@pytest.mark.asyncio
async def test_array_validation():
    """Test array validation."""
    config = ValidationConfig(max_array_length=5)
    validator = InputValidator(config)
    
    # Valid array
    data = ["item1", "item2", "item3"]
    validator.validate_list(data)  # Should not raise
    
    # Too many items
    data = ["item1", "item2", "item3", "item4", "item5", "item6"]
    with pytest.raises(ValueError, match="exceeds maximum length"):
        validator.validate_list(data)
    
    # Array with malicious content
    data = ["safe", "<script>alert(1)</script>"]
    with pytest.raises(ValueError, match="Invalid content detected"):
        validator.validate_list(data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])