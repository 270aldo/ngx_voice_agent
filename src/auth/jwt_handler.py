"""
Módulo para la gestión de tokens JWT.

Este módulo proporciona funciones para generar, validar y gestionar
tokens JWT utilizados para la autenticación y autorización en la API.
"""

import jwt
import time
import asyncio
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import os
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

# Import secrets manager and rotation service
try:
    from src.infrastructure.security import secrets_manager, get_secret
    from src.services.jwt_rotation_service import get_jwt_rotation_service
except ImportError:
    # Fallback for backward compatibility
    logger.warning("Secrets manager not available, using environment variables directly")
    secrets_manager = None
    get_jwt_rotation_service = None
    async def get_secret(key: str, required: bool = True) -> Optional[str]:
        value = os.getenv(key)
        if not value and required:
            logger.error(f"Required secret not found: {key}")
        return value

# JWT Configuration with secure defaults
_jwt_secret_cache = None
_jwt_secret_last_refresh = None
JWT_SECRET_REFRESH_INTERVAL = 3600  # Refresh secret from manager every hour

async def get_jwt_secret() -> str:
    """Get JWT secret with rotation support."""
    global _jwt_secret_cache, _jwt_secret_last_refresh
    
    # Try to use rotation service if available
    if get_jwt_rotation_service:
        try:
            rotation_service = await get_jwt_rotation_service()
            current_secret = rotation_service.get_current_secret()
            if current_secret:
                return current_secret
        except Exception as e:
            logger.warning(f"Error getting secret from rotation service: {e}")
    
    # Check if we need to refresh the secret from cache
    now = time.time()
    if (_jwt_secret_cache is None or 
        _jwt_secret_last_refresh is None or
        now - _jwt_secret_last_refresh > JWT_SECRET_REFRESH_INTERVAL):
        
        # Try to get from secrets manager
        if secrets_manager:
            secret = await get_secret("JWT_SECRET", required=False)
            if secret:
                _jwt_secret_cache = secret
                _jwt_secret_last_refresh = now
                return secret
        
        # Fallback to environment variable
        secret = os.getenv("JWT_SECRET")
        if secret:
            _jwt_secret_cache = secret
            _jwt_secret_last_refresh = now
            return secret
        
        # Check environment more securely
        environment = os.getenv("ENVIRONMENT", "production").lower()
        
        # Generate a secure default ONLY for development/test (with additional security checks)
        if environment in ["development", "test"]:
            # Additional security check: ensure we're not in a production-like environment
            production_indicators = [
                os.getenv("DATABASE_URL", "").startswith("postgres://"),
                os.getenv("SUPABASE_URL", "").endswith(".supabase.co"),
                os.getenv("REDIS_URL", "").startswith("redis://"),
                any(domain in os.getenv("ALLOWED_ORIGINS", "") for domain in [".com", ".io", ".net"])
            ]
            
            if any(production_indicators):
                logger.error("Production environment detected but JWT_SECRET not configured")
                raise ValueError("JWT_SECRET must be explicitly configured in production-like environments")
            
            logger.warning("JWT_SECRET not configured, generating a random secret for development")
            secret = secrets.token_urlsafe(32)
            os.environ["JWT_SECRET"] = secret
            _jwt_secret_cache = secret
            _jwt_secret_last_refresh = now
            return secret
        
        # Production requires explicit configuration - NO EXCEPTIONS
        logger.error("JWT_SECRET must be configured in production environment")
        raise ValueError("JWT_SECRET must be configured in production environment")
    
    return _jwt_secret_cache

async def get_all_valid_jwt_secrets() -> list:
    """Get all valid JWT secrets (for verification during rotation)."""
    secrets_list = []
    
    # Try rotation service first
    if get_jwt_rotation_service:
        try:
            rotation_service = await get_jwt_rotation_service()
            secrets_list = rotation_service.get_all_valid_secrets()
            if secrets_list:
                return secrets_list
        except Exception as e:
            logger.warning(f"Error getting secrets from rotation service: {e}")
    
    # Fallback to single secret
    secret = await get_jwt_secret()
    return [secret] if secret else []

# Synchronous wrapper for backward compatibility
def get_jwt_secret_sync() -> str:
    """Synchronous wrapper for get_jwt_secret."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we can't use run_until_complete
            # Return cached value or raise error
            if _jwt_secret_cache:
                return _jwt_secret_cache
            else:
                # Try environment variable as last resort
                secret = os.getenv("JWT_SECRET")
                if secret:
                    return secret
                raise ValueError("JWT_SECRET not available in cache")
        else:
            return loop.run_until_complete(get_jwt_secret())
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(get_jwt_secret())

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

class JWTHandler:
    """Clase para manejar operaciones relacionadas con JWT."""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Crea un token JWT de acceso.
        
        Args:
            data: Datos a incluir en el token (claims)
            expires_delta: Tiempo de expiración personalizado (opcional)
            
        Returns:
            str: Token JWT generado
        """
        to_encode = data.copy()
        
        # Establecer tiempo de expiración
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Añadir claims estándar (use timestamps for JWT standard compliance)
        now = datetime.utcnow()
        to_encode.update({
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "type": "access",
            "jti": secrets.token_urlsafe(16)  # JWT ID for revocation support
        })
        
        # Generar token con secret seguro
        try:
            jwt_secret = get_jwt_secret_sync()
            encoded_jwt = jwt.encode(to_encode, jwt_secret, algorithm=JWT_ALGORITHM)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error al generar token JWT: {str(e)}")
            raise
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Crea un token JWT de actualización.
        
        Args:
            data: Datos a incluir en el token (claims)
            expires_delta: Tiempo de expiración personalizado (opcional)
            
        Returns:
            str: Token JWT de actualización generado
        """
        to_encode = data.copy()
        
        # Establecer tiempo de expiración
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Añadir claims estándar (use timestamps for JWT standard compliance)
        now = datetime.utcnow()
        to_encode.update({
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "type": "refresh",
            "jti": secrets.token_urlsafe(16)  # JWT ID for revocation support
        })
        
        # Generar token con secret seguro
        try:
            jwt_secret = get_jwt_secret_sync()
            encoded_jwt = jwt.encode(to_encode, jwt_secret, algorithm=JWT_ALGORITHM)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error al generar token de actualización JWT: {str(e)}")
            raise
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decodifica y valida un token JWT con soporte para rotación de secrets.
        
        Args:
            token: Token JWT a decodificar
            
        Returns:
            Dict: Datos contenidos en el token
            
        Raises:
            jwt.PyJWTError: Si el token es inválido o ha expirado
        """
        # Try with rotation service if available
        if get_jwt_rotation_service:
            try:
                # Check if we're in an async context
                try:
                    current_loop = asyncio.get_running_loop()
                    # We're in an async context, but decode_token is sync
                    # Skip rotation service to avoid event loop conflicts
                    logger.debug("Running in async context, skipping rotation service")
                    raise RuntimeError("Skip rotation service in async context")
                except RuntimeError as loop_error:
                    if "async context" not in str(loop_error):
                        # No running loop, safe to create one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            secrets_list = loop.run_until_complete(get_all_valid_jwt_secrets())
                        finally:
                            loop.close()
                        
                        # Try to decode with each valid secret
                        last_error = None
                        for secret in secrets_list:
                            try:
                                # Add leeway for timing issues
                                payload = jwt.decode(
                                    token, 
                                    secret, 
                                    algorithms=[JWT_ALGORITHM],
                                    leeway=timedelta(seconds=300)  # 5 minute tolerance
                                )
                                return payload
                            except jwt.ExpiredSignatureError:
                                # Token is expired regardless of secret
                                logger.warning("Token JWT expirado")
                                raise
                            except jwt.InvalidTokenError as e:
                                # Try next secret
                                last_error = e
                                continue
                        
                        # If we get here, token was invalid with all secrets
                        if last_error:
                            logger.warning(f"Token JWT inválido con todos los secrets: {str(last_error)}")
                            raise last_error
                    else:
                        # We're in an async context, fallback to single secret
                        raise RuntimeError("Use single secret in async context")
                    
            except Exception as e:
                logger.warning(f"Error using rotation service, falling back to single secret: {e}")
        
        # Fallback to single secret
        try:
            jwt_secret = get_jwt_secret_sync()
            # Add leeway for timing issues (especially in tests)
            payload = jwt.decode(
                token, 
                jwt_secret, 
                algorithms=[JWT_ALGORITHM],
                leeway=timedelta(seconds=300)  # 5 minute tolerance for iat/exp timing
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token JWT expirado")
            raise
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token JWT inválido: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error al decodificar token JWT: {str(e)}")
            raise
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verifica un token JWT y su tipo.
        
        Args:
            token: Token JWT a verificar
            token_type: Tipo de token esperado ("access" o "refresh")
            
        Returns:
            Dict: Datos contenidos en el token si es válido
            
        Raises:
            ValueError: Si el token no es del tipo esperado
            jwt.PyJWTError: Si el token es inválido o ha expirado
        """
        payload = JWTHandler.decode_token(token)
        
        # Verificar tipo de token
        if payload.get("type") != token_type:
            logger.warning(f"Tipo de token incorrecto. Esperado: {token_type}, Recibido: {payload.get('type')}")
            raise ValueError(f"Token no es de tipo {token_type}")
        
        return payload
