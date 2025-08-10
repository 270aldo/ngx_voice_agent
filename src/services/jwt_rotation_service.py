"""
JWT Secret Rotation Service.

This service handles automatic rotation of JWT secrets to enhance security.
It implements a dual-key system to allow graceful rotation without invalidating
existing tokens immediately.
"""

import os
import json
import base64
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import logging
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import secrets

from src.config import settings
from src.integrations.supabase.client import supabase_client
from src.infrastructure.security.secrets_manager import secrets_manager
from src.utils.async_task_manager import AsyncTaskManager, get_task_registry
from src.core.constants import TimeConstants, SecurityConstants

logger = logging.getLogger(__name__)


class JWTRotationService:
    """Service for managing JWT secret rotation."""
    
    def __init__(self):
        """Initialize JWT rotation service."""
        self._current_secret = None
        self._previous_secret = None
        self._rotation_interval_days = SecurityConstants.REFRESH_TOKEN_EXPIRE_DAYS * 4  # Default rotation interval (approx 30 days)
        self._grace_period_days = SecurityConstants.REFRESH_TOKEN_EXPIRE_DAYS  # Keep old secret valid for 7 days
        self._last_rotation = None
        self._next_rotation = None
        self._supabase = None
        
    async def initialize(self):
        """Initialize the service and load current secrets."""
        self._supabase = supabase_client
        await self._load_secrets()
        
    async def _load_secrets(self):
        """Load current and previous JWT secrets from secure storage."""
        try:
            # Try to get secrets from secrets manager
            current_secret_data = await secrets_manager.get_secret("jwt_current_secret")
            
            if current_secret_data:
                secret_info = json.loads(current_secret_data)
                self._current_secret = secret_info["secret"]
                self._last_rotation = datetime.fromisoformat(secret_info["created_at"])
                self._next_rotation = datetime.fromisoformat(secret_info["next_rotation"])
                
                # Load previous secret if exists
                previous_secret_data = await secrets_manager.get_secret("jwt_previous_secret")
                if previous_secret_data:
                    previous_info = json.loads(previous_secret_data)
                    self._previous_secret = previous_info["secret"]
            else:
                # Initialize with current secret from environment
                await self._initialize_first_secret()
                
        except Exception as e:
            logger.error(f"Error loading JWT secrets: {e}")
            # Fall back to environment variable
            self._current_secret = settings.jwt_secret.get_secret_value() if settings.jwt_secret else None
            
    async def _initialize_first_secret(self):
        """Initialize the first JWT secret if none exists."""
        # Use existing secret from environment or generate new one
        if settings.jwt_secret:
            initial_secret = settings.jwt_secret.get_secret_value()
        else:
            initial_secret = self._generate_secret()
            
        now = datetime.now(timezone.utc)
        next_rotation = now + timedelta(days=self._rotation_interval_days)
        
        secret_info = {
            "secret": initial_secret,
            "created_at": now.isoformat(),
            "next_rotation": next_rotation.isoformat(),
            "rotation_count": 0
        }
        
        # Store in secrets manager
        await secrets_manager.set_secret("jwt_current_secret", json.dumps(secret_info))
        
        self._current_secret = initial_secret
        self._last_rotation = now
        self._next_rotation = next_rotation
        
        logger.info("Initialized first JWT secret")
        
    def _generate_secret(self) -> str:
        """Generate a cryptographically secure JWT secret."""
        # Generate 64 bytes (512 bits) of random data
        random_bytes = secrets.token_bytes(64)
        # Encode as base64 for string representation
        return base64.b64encode(random_bytes).decode('utf-8')
    
    async def rotate_secret(self, force: bool = False) -> bool:
        """
        Rotate JWT secret if needed.
        
        Args:
            force: Force rotation even if not due
            
        Returns:
            bool: True if rotation was performed
        """
        now = datetime.now(timezone.utc)
        
        # Check if rotation is needed
        if not force and self._next_rotation and now < self._next_rotation:
            logger.debug(f"Rotation not needed until {self._next_rotation}")
            return False
            
        try:
            # Generate new secret
            new_secret = self._generate_secret()
            
            # Move current to previous
            if self._current_secret:
                previous_info = {
                    "secret": self._current_secret,
                    "created_at": self._last_rotation.isoformat() if self._last_rotation else now.isoformat(),
                    "expired_at": (now + timedelta(days=self._grace_period_days)).isoformat()
                }
                await secrets_manager.set_secret("jwt_previous_secret", json.dumps(previous_info))
                self._previous_secret = self._current_secret
                
            # Set new current secret
            next_rotation = now + timedelta(days=self._rotation_interval_days)
            current_info = {
                "secret": new_secret,
                "created_at": now.isoformat(),
                "next_rotation": next_rotation.isoformat(),
                "rotation_count": await self._get_rotation_count() + 1
            }
            await secrets_manager.set_secret("jwt_current_secret", json.dumps(current_info))
            
            self._current_secret = new_secret
            self._last_rotation = now
            self._next_rotation = next_rotation
            
            # Log rotation event
            await self._log_rotation_event(success=True)
            
            logger.info(f"JWT secret rotated successfully. Next rotation: {next_rotation}")
            return True
            
        except Exception as e:
            logger.error(f"Error rotating JWT secret: {e}")
            await self._log_rotation_event(success=False, error=str(e))
            return False
    
    async def _get_rotation_count(self) -> int:
        """Get the current rotation count."""
        try:
            current_data = await secrets_manager.get_secret("jwt_current_secret")
            if current_data:
                info = json.loads(current_data)
                return info.get("rotation_count", 0)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Error parsing JWT rotation count: {e}")
            pass
        return 0
    
    async def _log_rotation_event(self, success: bool, error: Optional[str] = None):
        """Log rotation event to database."""
        try:
            event_data = {
                "event_type": "jwt_rotation",
                "success": success,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "next_rotation": self._next_rotation.isoformat() if self._next_rotation else None,
                "error_message": error
            }
            
            # Store in a security events table (if exists)
            if self._supabase:
                await self._supabase.table("security_events").insert(event_data).execute()
                
        except Exception as e:
            logger.error(f"Error logging rotation event: {e}")
    
    def get_current_secret(self) -> Optional[str]:
        """Get the current JWT secret."""
        return self._current_secret
    
    def get_previous_secret(self) -> Optional[str]:
        """Get the previous JWT secret (for grace period)."""
        return self._previous_secret
    
    def get_all_valid_secrets(self) -> List[str]:
        """Get all currently valid secrets (current + previous in grace period)."""
        secrets = []
        if self._current_secret:
            secrets.append(self._current_secret)
        if self._previous_secret:
            secrets.append(self._previous_secret)
        return secrets
    
    async def check_rotation_needed(self) -> bool:
        """Check if rotation is needed."""
        if not self._next_rotation:
            return True
            
        now = datetime.now(timezone.utc)
        return now >= self._next_rotation
    
    async def cleanup_expired_secrets(self):
        """Remove expired previous secrets."""
        try:
            previous_data = await secrets_manager.get_secret("jwt_previous_secret")
            if previous_data:
                info = json.loads(previous_data)
                expired_at = datetime.fromisoformat(info["expired_at"])
                
                if datetime.now(timezone.utc) > expired_at:
                    await secrets_manager.delete_secret("jwt_previous_secret")
                    self._previous_secret = None
                    logger.info("Cleaned up expired JWT secret")
                    
        except Exception as e:
            logger.error(f"Error cleaning up expired secrets: {e}")
    
    def get_rotation_status(self) -> Dict:
        """Get current rotation status."""
        now = datetime.now(timezone.utc)
        
        return {
            "current_secret_active": self._current_secret is not None,
            "previous_secret_active": self._previous_secret is not None,
            "last_rotation": self._last_rotation.isoformat() if self._last_rotation else None,
            "next_rotation": self._next_rotation.isoformat() if self._next_rotation else None,
            "rotation_due": self._next_rotation and now >= self._next_rotation,
            "rotation_interval_days": self._rotation_interval_days,
            "grace_period_days": self._grace_period_days
        }


class JWTRotationScheduler:
    """Scheduler for automatic JWT rotation."""
    
    def __init__(self, rotation_service: JWTRotationService):
        """Initialize rotation scheduler."""
        self.rotation_service = rotation_service
        self._running = False
        self._task = None
        self.task_manager: Optional[AsyncTaskManager] = None
        
        # Initialize async components
        asyncio.create_task(self._initialize_async())
    
    async def _initialize_async(self):
        """Async initialization including task manager setup."""
        try:
            # Get task manager from registry
            registry = get_task_registry()
            self.task_manager = await registry.register_service("jwt_rotation_scheduler")
            
            logger.info("JWTRotationScheduler async initialization complete")
        except Exception as e:
            logger.error(f"Failed to initialize JWTRotationScheduler async: {e}")
        
    async def start(self):
        """Start the rotation scheduler."""
        if self._running:
            return
            
        self._running = True
        
        if self.task_manager:
            self._task = await self.task_manager.create_task(
                self._rotation_loop(),
                name="rotation_loop"
            )
        else:
            # Fallback if task manager not ready
            self._task = asyncio.create_task(self._rotation_loop())
            
        logger.info("JWT rotation scheduler started")
        
    async def stop(self):
        """Stop the rotation scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("JWT rotation scheduler stopped")
        
    async def _rotation_loop(self):
        """Main rotation loop."""
        while self._running:
            try:
                # Check if rotation is needed
                if await self.rotation_service.check_rotation_needed():
                    await self.rotation_service.rotate_secret()
                    
                # Cleanup expired secrets
                await self.rotation_service.cleanup_expired_secrets()
                
                # Sleep for 1 hour before next check
                await asyncio.sleep(TimeConstants.JWT_ROTATION_CHECK)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rotation loop: {e}")
                # Sleep for 5 minutes on error
                await asyncio.sleep(300)
    
    async def cleanup(self):
        """
        Cleanup resources and stop background tasks.
        
        This should be called when shutting down the service.
        """
        logger.info("Cleaning up JWTRotationScheduler")
        
        try:
            # Stop the scheduler
            await self.stop()
            
            # Unregister from task registry
            if self.task_manager:
                registry = get_task_registry()
                await registry.unregister_service("jwt_rotation_scheduler")
                self.task_manager = None
            
            logger.info("JWTRotationScheduler cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during JWTRotationScheduler cleanup: {e}")


# Global instances
_rotation_service = None
_rotation_scheduler = None


async def get_jwt_rotation_service() -> JWTRotationService:
    """Get or create JWT rotation service instance."""
    global _rotation_service
    if _rotation_service is None:
        _rotation_service = JWTRotationService()
        await _rotation_service.initialize()
    return _rotation_service


async def start_jwt_rotation_scheduler():
    """Start the JWT rotation scheduler."""
    global _rotation_scheduler
    if _rotation_scheduler is None:
        service = await get_jwt_rotation_service()
        _rotation_scheduler = JWTRotationScheduler(service)
        await _rotation_scheduler.start()


async def stop_jwt_rotation_scheduler():
    """Stop the JWT rotation scheduler."""
    global _rotation_scheduler
    if _rotation_scheduler:
        await _rotation_scheduler.stop()
        _rotation_scheduler = None