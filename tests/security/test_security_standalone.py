"""
Standalone Security Tests for JWT and WebSocket Authentication

Isolated tests that don't require the full application context.
These tests focus on the core security functionality.
"""

import pytest
import os
import time
import asyncio
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add src to path for direct imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestJWTSecretEnforcement:
    """Test JWT_SECRET enforcement in production environments."""
    
    def test_jwt_secret_required_in_production(self):
        """Test that JWT_SECRET is required in production environment."""
        # Store original values
        original_secret = os.getenv("JWT_SECRET")
        original_env = os.getenv("ENVIRONMENT")
        
        try:
            # Clear JWT_SECRET and set production environment
            if "JWT_SECRET" in os.environ:
                del os.environ["JWT_SECRET"]
            os.environ["ENVIRONMENT"] = "production"
            
            # Clear any cached values
            from src.auth.jwt_handler import get_jwt_secret_sync
            import src.auth.jwt_handler as jwt_handler
            jwt_handler._jwt_secret_cache = None
            jwt_handler._jwt_secret_last_refresh = None
            
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
    
    def test_production_indicators_prevent_fallback(self):
        """Test that production-like indicators prevent development fallback."""
        # Store original values
        env_vars = ["JWT_SECRET", "ENVIRONMENT", "DATABASE_URL", "SUPABASE_URL"]
        original_values = {var: os.getenv(var) for var in env_vars}
        
        try:
            # Clean environment
            for var in env_vars:
                if var in os.environ:
                    del os.environ[var]
            
            # Set up production-like environment
            os.environ["ENVIRONMENT"] = "development"  # Try to fool it
            os.environ["DATABASE_URL"] = "postgres://user:pass@prod.example.com/db"
            
            # Clear cached values
            import src.auth.jwt_handler as jwt_handler
            jwt_handler._jwt_secret_cache = None
            jwt_handler._jwt_secret_last_refresh = None
            
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
    
    def test_jwt_secret_generation_in_clean_development(self):
        """Test that JWT_SECRET generation works in clean development."""
        # Store original values
        env_vars_to_clean = [
            "JWT_SECRET", "ENVIRONMENT", "DATABASE_URL", 
            "SUPABASE_URL", "REDIS_URL", "ALLOWED_ORIGINS"
        ]
        original_values = {var: os.getenv(var) for var in env_vars_to_clean}
        
        try:
            # Clean environment
            for var in env_vars_to_clean:
                if var in os.environ:
                    del os.environ[var]
            
            # Set clean development environment
            os.environ["ENVIRONMENT"] = "development"
            os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"
            
            # Clear cached values
            import src.auth.jwt_handler as jwt_handler
            jwt_handler._jwt_secret_cache = None
            jwt_handler._jwt_secret_last_refresh = None
            
            from src.auth.jwt_handler import get_jwt_secret_sync
            
            # Should generate a secret successfully
            secret = get_jwt_secret_sync()
            assert secret is not None
            assert len(secret) > 20  # Should be a proper secret
            
        finally:
            # Restore all original values
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                else:
                    os.environ.pop(var, None)


@pytest.mark.asyncio
class TestSessionManagerStandalone:
    """Test session manager functionality in isolation."""
    
    async def test_session_registration_and_validation(self):
        """Test session registration and validation."""
        # Import session manager directly
        from src.services.websocket.session_manager import WebSocketSessionManager
        
        # Create new instance for testing
        session_manager = WebSocketSessionManager()
        
        # Register a session
        user_id = "test_user_123"
        jti = "test_jwt_id"
        expires_at = time.time() + 3600  # 1 hour from now
        websocket_id = "ws_123"
        
        await session_manager.register_session(user_id, jti, expires_at, websocket_id)
        
        # Validate the session
        is_valid = await session_manager.validate_session_token(user_id, jti)
        assert is_valid is True
        
        # Test with wrong JTI
        is_valid = await session_manager.validate_session_token(user_id, "wrong_jti")
        assert is_valid is False
        
        # Clean up
        await session_manager.remove_session(user_id)
        
        # Should be invalid after removal
        is_valid = await session_manager.validate_session_token(user_id, jti)
        assert is_valid is False
    
    async def test_token_revocation(self):
        """Test token revocation functionality."""
        from src.services.websocket.session_manager import WebSocketSessionManager
        
        session_manager = WebSocketSessionManager()
        
        jti = "test_revoke_jwt_id"
        expires_at = time.time() + 3600
        
        # Initially not revoked
        is_revoked = await session_manager.is_token_revoked(jti)
        assert is_revoked is False
        
        # Revoke a token
        await session_manager.revoke_token(jti, expires_at)
        
        # Check that it's revoked
        is_revoked = await session_manager.is_token_revoked(jti)
        assert is_revoked is True
    
    async def test_user_session_revocation(self):
        """Test revoking all sessions for a user."""
        from src.services.websocket.session_manager import WebSocketSessionManager
        
        session_manager = WebSocketSessionManager()
        
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
    
    async def test_expired_session_cleanup(self):
        """Test cleanup of expired sessions."""
        from src.services.websocket.session_manager import WebSocketSessionManager
        
        session_manager = WebSocketSessionManager()
        
        user_id = "test_expired_user"
        jti = "test_expired_jwt"
        expires_at = time.time() - 10  # Expired 10 seconds ago
        websocket_id = "ws_expired"
        
        # Register expired session
        await session_manager.register_session(user_id, jti, expires_at, websocket_id)
        
        # Should be invalid due to expiration
        is_valid = await session_manager.validate_session_token(user_id, jti)
        assert is_valid is False
        
        # Session should be automatically removed
        assert user_id not in session_manager.active_sessions


class TestJWTHandlerStandalone:
    """Test JWT handler functionality in isolation."""
    
    def test_jwt_token_creation_and_validation(self):
        """Test JWT token creation and validation."""
        # Ensure we have a JWT secret
        os.environ["JWT_SECRET"] = "test_secret_key_for_testing_purposes_only"
        os.environ["ENVIRONMENT"] = "test"
        
        try:
            from src.auth.jwt_handler import JWTHandler
            
            # Create a test token
            token_data = {
                "sub": "test_user",
                "username": "test@example.com",
                "role": "user"
            }
            
            # Create access token
            access_token = JWTHandler.create_access_token(token_data)
            assert access_token is not None
            assert len(access_token) > 50  # JWT tokens are long
            
            # Decode the token
            decoded = JWTHandler.decode_token(access_token)
            assert decoded["sub"] == "test_user"
            assert decoded["username"] == "test@example.com" 
            assert decoded["role"] == "user"
            assert decoded["type"] == "access"
            assert "jti" in decoded  # JWT ID should be present
            assert "exp" in decoded  # Expiration should be present
            assert "iat" in decoded  # Issued at should be present
            
        finally:
            # Clean up test environment
            if "JWT_SECRET" in os.environ:
                del os.environ["JWT_SECRET"]
            if os.getenv("ENVIRONMENT") == "test":
                del os.environ["ENVIRONMENT"]
    
    def test_jwt_token_type_validation(self):
        """Test JWT token type validation."""
        os.environ["JWT_SECRET"] = "test_secret_key_for_testing_purposes_only"
        os.environ["ENVIRONMENT"] = "test"
        
        try:
            from src.auth.jwt_handler import JWTHandler
            
            token_data = {"sub": "test_user"}
            
            # Create access and refresh tokens
            access_token = JWTHandler.create_access_token(token_data)
            refresh_token = JWTHandler.create_refresh_token(token_data)
            
            # Verify access token
            access_payload = JWTHandler.verify_token(access_token, "access")
            assert access_payload["type"] == "access"
            
            # Verify refresh token
            refresh_payload = JWTHandler.verify_token(refresh_token, "refresh") 
            assert refresh_payload["type"] == "refresh"
            
            # Should fail when using wrong type
            with pytest.raises(ValueError, match="Token no es de tipo refresh"):
                JWTHandler.verify_token(access_token, "refresh")
                
        finally:
            if "JWT_SECRET" in os.environ:
                del os.environ["JWT_SECRET"]
            if os.getenv("ENVIRONMENT") == "test":
                del os.environ["ENVIRONMENT"]


if __name__ == "__main__":
    # Run the standalone tests
    pytest.main([__file__, "-v"])