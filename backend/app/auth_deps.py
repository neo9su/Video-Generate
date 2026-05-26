"""JWT authentication dependency for protected routes."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from .config import settings
from .database import get_db
from .models.user import User

security = HTTPBearer()


async def get_current_user(
    token: str = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode JWT, fetch user from DB, return user object.

    Raises 401 if the token is invalid or the user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: Optional[int] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_id = int(user_id)  # JWT sub is always string, convert to int
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


async def get_optional_user(
    token: Optional[str] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of 401 on missing/invalid token."""
    if token is None:
        return None
    try:
        return await get_current_user(token=token, db=db)  # type: ignore[arg-type]
    except HTTPException:
        return None
