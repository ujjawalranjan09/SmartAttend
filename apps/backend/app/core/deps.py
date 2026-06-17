import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)

# Optional auth — does not raise if no token present
oauth2_scheme_without_error = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", auto_error=False
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except ValueError:
        raise credentials_exception

    from app.core.redis import is_token_blacklisted

    # Check if token has a JTI and if it's blacklisted
    jti = payload.get("jti")
    if jti:
        try:
            blacklisted = await is_token_blacklisted(jti)
            if blacklisted:
                raise credentials_exception
        except Exception:
            pass  # If Redis is down, allow through (degraded mode)

    svc = UserService(db)
    user = await svc.get_by_id(user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(*roles: UserRole):
    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in roles]}",
            )
        return current_user
    return _checker


require_admin    = require_roles(UserRole.ADMIN)
require_faculty  = require_roles(UserRole.FACULTY, UserRole.HOD, UserRole.ADMIN)
require_hod      = require_roles(UserRole.HOD, UserRole.ADMIN)
require_student  = require_roles(UserRole.STUDENT)


async def get_user_institution_id(
    current_user: User = Depends(get_current_user),
) -> uuid.UUID | None:
    if current_user.role == UserRole.ADMIN and current_user.institution_id is None:
        return None
    return current_user.institution_id


def filter_by_institution(query: Select, institution_id: uuid.UUID | None) -> Select:
    if institution_id is None:
        return query
    model = query.column_descriptions[0]["entity"]
    if model is None:
        return query
    return query.where(model.institution_id == institution_id)
