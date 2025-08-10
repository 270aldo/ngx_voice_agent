"""
Authentication endpoints for NGX Command Center

Handles user registration, login, and token management.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Response
from fastapi.security import HTTPBearer
from datetime import datetime, timedelta
from typing import Dict, Any
import uuid

from src.models.user import UserCreate, User, Token, Organization
from src.core.auth.deps import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    get_current_user
)
from src.api.middleware.csrf_protection import csrf_protection
from src.integrations.supabase.client import supabase_client
from src.config.settings import settings
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)
router = APIRouter()


@router.post("/register", response_model=Token)
async def register(user_data: UserCreate) -> Token:
    """
    Register a new user and organization.
    
    Creates a new organization and user account.
    """
    supabase = supabase_client
    
    try:
        # Check if email already exists
        existing = supabase.table("users").select("id").eq(
            "email", user_data.email
        ).execute()
        
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create organization first
        org_name = user_data.organization_name or f"{user_data.full_name}'s Organization"
        org_data = {
            "id": str(uuid.uuid4()),
            "name": org_name,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "plan": "starter",
            "settings": {}
        }
        
        org_response = supabase.table("organizations").insert(org_data).execute()
        
        if not org_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create organization"
            )
        
        # Create user
        user_id = str(uuid.uuid4())
        hashed_password = get_password_hash(user_data.password)
        
        user_db_data = {
            "id": user_id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "hashed_password": hashed_password,
            "organization_id": org_data["id"],
            "role": "owner",  # First user is owner
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        user_response = supabase.table("users").insert(user_db_data).execute()
        
        if not user_response.data:
            # Rollback organization creation
            supabase.table("organizations").delete().eq("id", org_data["id"]).execute()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        # Create access token
        access_token = create_access_token(
            data={
                "sub": user_id,
                "email": user_data.email,
                "organization_id": org_data["id"]
            }
        )
        
        logger.info(f"New user registered: {user_data.email}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(email: str, password: str) -> Token:
    """
    Login with email and password.
    
    Returns JWT access token on success.
    """
    supabase = supabase_client
    
    try:
        # Get user by email
        user_response = supabase.table("users").select("*").eq(
            "email", email
        ).single().execute()
        
        if not user_response.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user_data = user_response.data
        
        # Verify password
        if not verify_password(password, user_data["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user_data["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Update last login
        supabase.table("users").update({
            "last_login": datetime.utcnow().isoformat()
        }).eq("id", user_data["id"]).execute()
        
        # Create access token
        access_token = create_access_token(
            data={
                "sub": user_data["id"],
                "email": user_data["email"],
                "organization_id": user_data["organization_id"]
            }
        )
        
        logger.info(f"User logged in: {email}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user information.
    
    Returns the authenticated user's profile.
    """
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_user)
) -> Token:
    """
    Refresh access token.
    
    Returns a new JWT access token.
    """
    # Create new access token
    access_token = create_access_token(
        data={
            "sub": str(current_user.id),
            "email": current_user.email,
            "organization_id": str(current_user.organization_id)
        }
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/organization", response_model=Organization)
async def get_organization_info(
    current_user: User = Depends(get_current_user)
) -> Organization:
    """
    Get current organization information.
    
    Returns the user's organization details.
    """
    supabase = supabase_client
    
    try:
        response = supabase.table("organizations").select("*").eq(
            "id", str(current_user.organization_id)
        ).single().execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        org_data = response.data
        
        return Organization(
            id=org_data["id"],
            name=org_data["name"],
            created_at=datetime.fromisoformat(org_data["created_at"]),
            updated_at=datetime.fromisoformat(org_data["updated_at"]),
            plan=org_data.get("plan", "starter"),
            settings=org_data.get("settings", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get organization info"
        )


@router.get("/csrf")
async def get_csrf_token(response: Response) -> Dict[str, str]:
    """
    Get CSRF token for client-side protection.
    
    Returns a CSRF token that must be included in state-changing requests.
    The token is also set as a cookie for double-submit validation.
    """
    try:
        # Generate and set CSRF token
        token = csrf_protection.generate_token_response(response)
        
        logger.info("CSRF token generated for client")
        
        return {
            "csrf_token": token,
            "expires_in": csrf_protection.config.token_ttl
        }
        
    except Exception as e:
        logger.error(f"Error generating CSRF token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate CSRF token"
        )