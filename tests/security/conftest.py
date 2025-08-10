"""
Configuración para pruebas de seguridad.

Este módulo proporciona fixtures para las pruebas de seguridad.
"""

import pytest
from fastapi.testclient import TestClient
from tests.security.security_test_config import (
    get_test_client, create_test_user_token, create_test_admin_token,
    get_auth_headers, JWT_SECRET, JWT_ALGORITHM
)
from src.api.middleware.rate_limiter import RateLimiter

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    Fixture que resetea el rate limiter antes y después de cada test.
    """
    # Reset antes del test
    from src.api.main import app
    if hasattr(app.state, 'rate_limiter'):
        app.state.rate_limiter.reset_state()
    
    yield
    
    # Reset después del test
    if hasattr(app.state, 'rate_limiter'):
        app.state.rate_limiter.reset_state()

@pytest.fixture
def isolated_security_client():
    """
    Fixture que proporciona un cliente de prueba aislado con rate limiter limpio.
    Crea una nueva instancia de la aplicación para evitar interferencias entre tests.
    
    Returns:
        TestClient: Cliente de prueba para la API con estado limpio.
    """
    # Forzar recreación del cliente para tener estado limpio
    import importlib
    import sys
    
    # Recargar el módulo main para obtener una app fresca
    if 'src.api.main' in sys.modules:
        importlib.reload(sys.modules['src.api.main'])
    
    from src.api.main import app
    from fastapi.testclient import TestClient
    
    return TestClient(app)

@pytest.fixture
def security_client():
    """
    Fixture que proporciona un cliente de prueba para las pruebas de seguridad.
    
    Returns:
        TestClient: Cliente de prueba para la API.
    """
    return get_test_client()

@pytest.fixture
def test_user():
    """
    Fixture que proporciona un usuario de prueba.
    
    Returns:
        dict: Datos del usuario de prueba.
    """
    return {
        "user_id": "test_user_id",
        "username": "test_user",
        "password": "test_password",
        "permissions": ["read:analytics", "read:models"]
    }

@pytest.fixture
def test_admin():
    """
    Fixture que proporciona un administrador de prueba.
    
    Returns:
        dict: Datos del administrador de prueba.
    """
    return {
        "user_id": "admin_user_id",
        "username": "admin_user",
        "password": "admin_password",
        "role": "admin"
    }

@pytest.fixture
def user_token(test_user):
    """
    Fixture que proporciona un token de usuario para pruebas.
    
    Args:
        test_user: Fixture con datos del usuario de prueba.
        
    Returns:
        str: Token JWT para el usuario de prueba.
    """
    return create_test_user_token(
        user_id=test_user["user_id"],
        username=test_user["username"],
        permissions=test_user["permissions"]
    )

@pytest.fixture
def admin_token(test_admin):
    """
    Fixture que proporciona un token de administrador para pruebas.
    
    Args:
        test_admin: Fixture con datos del administrador de prueba.
        
    Returns:
        str: Token JWT para el administrador de prueba.
    """
    return create_test_admin_token(
        user_id=test_admin["user_id"],
        username=test_admin["username"]
    )

@pytest.fixture
def auth_headers(user_token):
    """
    Fixture que proporciona encabezados de autorización para un usuario normal.
    
    Args:
        user_token: Fixture con el token del usuario.
        
    Returns:
        dict: Encabezados de autorización.
    """
    return get_auth_headers(user_token)

@pytest.fixture
def admin_headers(admin_token):
    """
    Fixture que proporciona encabezados de autorización para un administrador.
    
    Args:
        admin_token: Fixture con el token del administrador.
        
    Returns:
        dict: Encabezados de autorización.
    """
    return get_auth_headers(admin_token)
