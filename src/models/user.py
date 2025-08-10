"""
User model for NGX Command Center

Defines the user structure for authentication and authorization.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    full_name: str
    is_active: bool = True
    role: str = "user"  # user, admin, owner


class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=8)
    organization_name: Optional[str] = None


class UserUpdate(BaseModel):
    """User update model"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    role: Optional[str] = None


class User(UserBase):
    """Complete user model"""
    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserInDB(User):
    """User model with hashed password"""
    hashed_password: str


class Organization(BaseModel):
    """Organization model"""
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    plan: str = "starter"  # starter, pro, enterprise
    settings: dict = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class TokenData(BaseModel):
    """Token payload data"""
    sub: str  # user_id
    email: str
    organization_id: str
    exp: datetime