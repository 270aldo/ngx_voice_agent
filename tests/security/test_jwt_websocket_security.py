"""
Security Tests for JWT and WebSocket Authentication

Tests the critical security fixes implemented for:
1. JWT_SECRET enforcement in production
2. WebSocket authentication with JWT tokens
3. Session management and revocation
"""

import pytest
import asyncio
import os
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Test the JWT Secret enforcement
class TestJWTSecretEnforcement:
    """Test JWT_SECRET enforcement in production environments."""
    
    def test_jwt_secret_required_in_production(self):
        """Test that JWT_SECRET is required in production environment."""
        # Clear any existing JWT_SECRET
        original_secret = os.getenv("JWT_SECRET")
        original_env = os.getenv("ENVIRONMENT")
        
        try:
            # Remove JWT_SECRET from environment
            if "JWT_SECRET" in os.environ:
                del os.environ["JWT_SECRET"]
            
            # Set production environment
            os.environ["ENVIRONMENT"] = "production"
            
            # Import after setting environment
            from src.auth.jwt_handler import get_jwt_secret_sync
            
            # Should raise ValueError in production without JWT_SECRET
            with pytest.raises(ValueError, match="JWT_SECRET must be configured"):
                get_jwt_secret_sync()
                
        finally:
            # Restore original values
            if original_secret:
                os.environ["JWT_SECRET"] = original_secret
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            else:
                os.environ.pop("ENVIRONMENT", None)
    
    def test_production_indicators_prevent_development_fallback(self):
        """Test that production-like indicators prevent development fallback."""
        original_values = {}
        env_vars_to_test = [
            "JWT_SECRET", "ENVIRONMENT", "DATABASE_URL", 
            "SUPABASE_URL", "REDIS_URL", "ALLOWED_ORIGINS"
        ]
        
        try:
            # Store original values
            for var in env_vars_to_test:
                original_values[var] = os.getenv(var)
                if var in os.environ:
                    del os.environ[var]
            
            # Set up production-like environment without JWT_SECRET
            os.environ["ENVIRONMENT"] = "development"  # Try to fool it
            os.environ["DATABASE_URL"] = "postgres://user:pass@prod.example.com/db"
            
            from src.auth.jwt_handler import get_jwt_secret_sync
            
            # Should still raise error due to production indicators
            with pytest.raises(ValueError, match="explicitly configured in production-like"):
                get_jwt_secret_sync()
                
        finally:
            # Restore all original values
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                else:
                    os.environ.pop(var, None)
    
    def test_jwt_secret_works_in_development(self):
        """Test that JWT_SECRET generation works in true development."""
        original_values = {}
        env_vars_to_clean = [
            "JWT_SECRET", "ENVIRONMENT", "DATABASE_URL", 
            "SUPABASE_URL", "REDIS_URL", "ALLOWED_ORIGINS"
        ]
        
        try:
            # Store original values and clean environment
            for var in env_vars_to_clean:
                original_values[var] = os.getenv(var)
                if var in os.environ:
                    del os.environ[var]
            
            # Set clean development environment
            os.environ["ENVIRONMENT"] = "development"
            os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"
            
            from src.auth.jwt_handler import get_jwt_secret_sync
            
            # Should generate a secret successfully
            secret = get_jwt_secret_sync()
            assert secret is not None
            assert len(secret) > 10  # Should be a proper secret
            
        finally:
            # Restore all original values
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                else:
                    os.environ.pop(var, None)


@pytest.mark.asyncio
class TestWebSocketSecurity:
    """Test WebSocket authentication and security."""
    
    async def test_websocket_rejects_invalid_token(self):
        """Test that WebSocket connections reject invalid tokens."""
        from src.services.websocket.websocket_manager import authenticate_websocket
        
        # Test with invalid token
        result = await authenticate_websocket("invalid_token")
        assert result is None
    
    async def test_websocket_rejects_expired_token(self):
        """Test that WebSocket connections reject expired tokens."""
        from src.auth.jwt_handler import JWTHandler
        from src.services.websocket.websocket_manager import authenticate_websocket
        
        # Create an expired token
        past_time = datetime.utcnow() - timedelta(hours=1)
        token_data = {
            "sub": "test_user",
            "exp": int(past_time.timestamp()),
            "iat": int(past_time.timestamp()),
            "type": "access"
        }
        
        # This would normally create an expired token, but let's mock it
        with patch('src.auth.jwt_handler.JWTHandler.verify_token') as mock_verify:
            mock_verify.side_effect = Exception("Token expired")
            
            result = await authenticate_websocket("expired_token")
            assert result is None
    
    async def test_websocket_requires_access_token_type(self):
        """Test that WebSocket only accepts access tokens."""
        from src.services.websocket.websocket_manager import authenticate_websocket
        
        # Mock a valid refresh token (wrong type)
        with patch('src.auth.jwt_handler.JWTHandler.verify_token') as mock_verify:
            mock_verify.return_value = {
                "sub": "test_user",
                "type": "refresh",  # Wrong type
                "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
            }
            
            result = await authenticate_websocket("refresh_token")
            assert result is None


@pytest.mark.asyncio
class TestSessionManagement:
    """Test session management and revocation."""
    
    async def test_session_registration_and_validation(self):
        """Test session registration and validation."""
        from src.services.websocket.session_manager import session_manager
        
        # Register a session
        user_id = "test_user_123"
        jti = "test_jwt_id"
        expires_at = time.time() + 3600  # 1 hour from now
        websocket_id = "ws_123"
        
        await session_manager.register_session(user_id, jti, expires_at, websocket_id)
        
        # Validate the session
        is_valid = await session_manager.validate_session_token(user_id, jti)
        assert is_valid is True
        
        # Clean up
        await session_manager.remove_session(user_id)
    
    async def test_token_revocation(self):
        """Test token revocation functionality."""
        from src.services.websocket.session_manager import session_manager
        
        jti = "test_revoke_jwt_id"
        expires_at = time.time() + 3600
        
        # Revoke a token
        await session_manager.revoke_token(jti, expires_at)
        
        # Check that it's revoked
        is_revoked = await session_manager.is_token_revoked(jti)
        assert is_revoked is True
    
    async def test_user_session_revocation(self):
        """Test revoking all sessions for a user."""
        from src.services.websocket.session_manager import session_manager
        
        user_id = "test_user_revoke"
        jti = "test_jwt_revoke"
        expires_at = time.time() + 3600
        websocket_id = "ws_revoke"
        
        # Register session
        await session_manager.register_session(user_id, jti, expires_at, websocket_id)
        
        # Verify it's valid
        is_valid = await session_manager.validate_session_token(user_id, jti)
        assert is_valid is True
        
        # Revoke all user sessions
        await session_manager.revoke_all_user_sessions(user_id)
        
        # Verify token is now revoked
        is_revoked = await session_manager.is_token_revoked(jti)
        assert is_revoked is True
        
        # Verify session is removed
        is_valid = await session_manager.validate_session_token(user_id, jti)
        assert is_valid is False


class TestSecurityLogging:
    """Test security event logging."""
    
    def test_security_events_are_logged(self):
        """Test that security events are properly logged."""
        import logging
        from unittest.mock import MagicMock
        
        # Mock logger to capture log calls
        mock_logger = MagicMock()
        
        with patch('src.services.websocket.websocket_manager.logger', mock_logger):
            # Import after patching
            import asyncio
            from src.services.websocket.websocket_manager import authenticate_websocket
            
            # Test authentication failure logging
            asyncio.run(authenticate_websocket("invalid_token"))
            
            # Verify security event was logged
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args
            assert "security_event" in str(call_args)


@pytest.mark.asyncio 
class TestIntegrationSecurity:
    """Integration tests for security features."""
    
    async def test_end_to_end_websocket_security(self):
        """Test complete WebSocket security flow."""
        # This would test the complete flow:
        # 1. User logs in and gets JWT
        # 2. Uses JWT to connect to WebSocket
        # 3. WebSocket validates token and registers session
        # 4. User logs out, token is revoked
        # 5. WebSocket connection is terminated
        
        # Note: This is a placeholder for a more complete integration test
        # that would require a test client and actual WebSocket connection
        pass


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])