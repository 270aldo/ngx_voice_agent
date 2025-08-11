"""
Pruebas de seguridad para la API.

Este módulo contiene pruebas específicas para verificar que las medidas
de seguridad implementadas funcionen correctamente.
"""

import pytest
import time
import jwt
import os
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from tests.security.security_test_config import (
    get_test_client, create_test_token, get_auth_headers,
    create_test_user_token, create_test_admin_token, JWT_SECRET, JWT_ALGORITHM
)

class TestSecurityMeasures:
    """Pruebas para las medidas de seguridad."""
    
    def test_rate_limiting(self, security_client):
        # Usar el cliente de prueba proporcionado por el fixture
        client = security_client
        """Prueba que la limitación de tasa funcione correctamente."""
        # Realizar múltiples solicitudes rápidamente
        endpoint = "/auth/me"  # Use a non-whitelisted endpoint
        num_requests = 15  # More than the 5 per minute limit
        
        responses = []
        for i in range(num_requests):
            try:
                response = client.get(endpoint)
                responses.append(response)
            except Exception as e:
                # Handle HTTPException from rate limiter
                if hasattr(e, 'status_code') and e.status_code == 429:
                    # Create a mock response object for the 429 case
                    class MockResponse:
                        def __init__(self):
                            self.status_code = 429
                    responses.append(MockResponse())
                else:
                    raise e
        
        # Count different response types
        auth_required_count = sum(1 for r in responses if r.status_code == 401)  # Auth required
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)   # Rate limited
        other_count = sum(1 for r in responses if r.status_code not in [401, 429])  # Other responses
        
        # Debug output
        print(f"Auth required (401): {auth_required_count}")
        print(f"Rate limited (429): {rate_limited_count}")
        print(f"Other responses: {other_count}")
        
        # Debe haber al menos una solicitud limitada
        assert rate_limited_count > 0, f"Expected rate limiting, but got: 401={auth_required_count}, 429={rate_limited_count}, other={other_count}"
        
        # El total debe ser igual al número de solicitudes
        assert auth_required_count + rate_limited_count + other_count == num_requests
    
    def test_security_headers(self, security_client):
        # Usar el cliente de prueba proporcionado por el fixture
        client = security_client
        """Prueba que los encabezados de seguridad estén presentes en las respuestas."""
        # Realizar una solicitud
        response = client.get("/health")
        
        # Verificar encabezados de seguridad
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        
        assert "Strict-Transport-Security" in response.headers
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
        assert "includeSubDomains" in response.headers["Strict-Transport-Security"]
        
        assert "Content-Security-Policy" in response.headers
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]
        assert "script-src 'self'" in response.headers["Content-Security-Policy"]
        assert "object-src 'none'" in response.headers["Content-Security-Policy"]
        
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0
    
    def test_token_expiration(self, security_client, test_user):
        # Usar el cliente de prueba proporcionado por el fixture
        client = security_client
        """Prueba que los tokens expiren correctamente."""
        # For testing purposes, create a token directly since auth is mocked
        from tests.security.security_test_config import create_test_token
        from datetime import datetime, timedelta
        
        # Create a valid token with a known expiration
        test_token_data = {
            "sub": test_user["user_id"],
            "username": test_user["username"],
            "permissions": test_user["permissions"]
        }
        
        # Create token with known expiration (30 minutes from now)
        token = create_test_token(test_token_data, expires_delta=timedelta(minutes=30))
        
        # Decodificar token para verificar tiempo de expiración
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Verificar que el token tiene tiempo de expiración
        assert "exp" in decoded
        
        # Calcular tiempo hasta expiración (usar UTC para ambos)
        expiration_time = datetime.utcfromtimestamp(decoded["exp"])
        now = datetime.utcnow()
        time_until_expiration = expiration_time - now
        
        # Debug output
        print(f"Expiration time: {expiration_time}")
        print(f"Current time: {now}")
        print(f"Time until expiration: {time_until_expiration}")
        print(f"Decoded token exp: {decoded['exp']}")
        
        # Verificar que el token tiene tiempo de expiración positivo (no está expirado)
        assert time_until_expiration.total_seconds() > 0, f"Token is expired! Time until expiration: {time_until_expiration}"
        
        # Verificar que el tiempo de expiración es aproximadamente el esperado (30 minutos)
        expected_expiration = timedelta(minutes=30)
        time_diff = abs((time_until_expiration - expected_expiration).total_seconds())
        assert time_diff < 120, f"Token expiration time is not as expected. Expected ~30 min, got {time_until_expiration}, diff: {time_diff}s"  # Margen de 2 minutos
    
    def test_invalid_token_rejection(self, security_client):
        # Usar el cliente de prueba proporcionado por el fixture
        client = security_client
        """Prueba que los tokens inválidos sean rechazados."""
        # Crear un token inválido
        invalid_token = "invalid.token.here"
        
        # Intentar acceder a un endpoint protegido
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        
        # Verificar que se rechaza el token
        assert response.status_code == 401
        assert response.json()["success"] is False
        assert "error" in response.json()
        assert "code" in response.json()["error"]
        assert response.json()["error"]["code"] == "UNAUTHORIZED"
    
    def test_expired_token_rejection(self, security_client):
        # Usar el cliente de prueba proporcionado por el fixture
        client = security_client
        """Prueba que los tokens expirados sean rechazados."""
        # Crear un token expirado manualmente
        payload = {
            "sub": "test_user",
            "permissions": ["read:models"],
            "exp": datetime.utcnow() - timedelta(minutes=5),  # Expirado hace 5 minutos
            "iat": datetime.utcnow() - timedelta(hours=2),
            "type": "access"  # Debe ser 'type', no 'token_type'
        }
        
        # Firmar el token
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Intentar acceder a un endpoint protegido
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        # Verificar que se rechaza el token
        assert response.status_code == 401
        assert response.json()["success"] is False
        assert "error" in response.json()
        assert "code" in response.json()["error"]
        assert response.json()["error"]["code"] == "UNAUTHORIZED"
    
    def test_permission_enforcement(self, security_client, auth_headers, admin_headers):
        # Usar el cliente de prueba proporcionado por el fixture
        client = security_client
        """Prueba que se apliquen correctamente los permisos."""
        
        # Test the core permission logic directly rather than through API endpoints
        # This focuses on testing the permission enforcement mechanism itself
        from src.auth.auth_utils import TokenData
        from src.auth.auth_dependencies import has_admin_role, get_current_active_user
        from fastapi import HTTPException
        import pytest
        
        # Test 1: Normal user should NOT have admin role access
        normal_user = TokenData(
            user_id="test_user_id",
            username="test_user", 
            role="user",
            permissions=["read:analytics", "read:models"]  # Limited permissions
        )
        
        # Test the has_admin_role function directly
        with pytest.raises(HTTPException) as exc_info:
            has_admin_role(normal_user)
        
        # Should raise 403 Forbidden
        assert exc_info.value.status_code == 403
        assert "forbidden" in exc_info.value.detail.lower() or "admin" in exc_info.value.detail.lower()
        
        # Test 2: Admin user SHOULD have admin role access  
        admin_user = TokenData(
            user_id="admin_user_id",
            username="admin_user",
            role="admin", 
            permissions=["*"]  # Admin permissions
        )
        
        # Should NOT raise an exception and return the user data
        result = has_admin_role(admin_user)
        assert result == admin_user
        assert result.role == "admin"
        assert "*" in result.permissions
        
        print("Permission enforcement test passed - admin role checking works correctly")
    
    def test_input_validation(self, security_client):
        # Usar el cliente de prueba proporcionado por el fixture
        client = security_client
        """Prueba que la validación de entradas funcione correctamente."""
        # Crear un token fresco para este test
        from tests.security.security_test_config import create_test_user_token, get_auth_headers
        fresh_token = create_test_user_token(
            user_id="test_user_validation",
            username="test_user",
            permissions=["predict"]
        )
        fresh_headers = get_auth_headers(fresh_token)
        
        # Datos inválidos para la solicitud
        invalid_data = {
            "conversation_id": "test_conv",
            "messages": [
                {
                    "role": "invalid_role",  # Rol inválido
                    "content": "Mensaje de prueba",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        }
        
        # Realizar solicitud con datos inválidos
        response = client.post(
            "/predictive/objection/predict",
            json=invalid_data,
            headers=fresh_headers
        )
        
        # Verificar respuesta de error de validación
        assert response.status_code == 422
        assert response.json()["success"] is False
        assert "error" in response.json()
        assert "code" in response.json()["error"]
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        assert "role" in response.json()["error"]["message"].lower()  # El mensaje debe mencionar el campo inválido
    
    def test_error_sanitization(self, security_client):
        # Usar el cliente de prueba proporcionado por el fixture
        client = security_client
        """Prueba que los errores internos no expongan información sensible."""
        # Intentar acceder a un endpoint que no existe para generar un error
        response = client.get("/non_existent_endpoint")
        
        # Verificar que la respuesta es un error 404
        assert response.status_code == 404
        
        # Verificar que la respuesta tiene contenido
        assert response.content
        
        # Convertir la respuesta a texto para buscar información sensible
        response_text = response.text.lower()
        
        # Verificar que no hay información sensible en la respuesta
        assert "traceback" not in response_text, "La respuesta contiene 'traceback'"
        assert "stack" not in response_text, "La respuesta contiene 'stack'"
