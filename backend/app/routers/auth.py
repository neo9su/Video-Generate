"""Authentication routes — register, login, profile management."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..config import settings
from ..database import get_db
from ..models.user import User
from ..auth_deps import get_current_user

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Schemas ───────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email address")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── Helpers ───────────────────────────────────────────────────────────────

def create_access_token(user_id: int) -> str:
    """Create a JWT access token for the given user ID."""
    expire = datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_expiration)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.username,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


# ─── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account.

    Returns a JWT access token and the new user's profile.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check if username (name) already exists
    name = req.name.strip() if req.name.strip() else req.email.split("@")[0]
    result = await db.execute(select(User).where(User.username == name))
    if result.scalar_one_or_none():
        # Append a suffix to make it unique
        import random
        name = f"{name}_{random.randint(100, 999)}"

    # Create user
    user = User(
        email=req.email,
        username=name,
        hashed_password=pwd_context.hash(req.password),
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await db.commit()  # Commit immediately so subsequent requests can read

    token = create_access_token(user.id)
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=_user_to_response(user),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate a user and return a JWT access token."""
    result = await db.execute(
        select(User).where(User.email == req.email.strip().lower())
    )
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    token = create_access_token(user.id)
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=_user_to_response(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get the profile of the currently authenticated user."""
    return _user_to_response(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    req: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the profile of the currently authenticated user."""
    if req.name is not None:
        current_user.username = req.name.strip()
    if req.email is not None:
        # Check uniqueness
        result = await db.execute(
            select(User).where(User.email == req.email.strip().lower(), User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )
        current_user.email = req.email.strip().lower()

    await db.flush()
    await db.refresh(current_user)
    return _user_to_response(current_user)
