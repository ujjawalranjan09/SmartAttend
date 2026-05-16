from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    decode_token, verify_totp, generate_totp_secret
)
from app.schemas.auth import TokenResponse, LoginRequest, RefreshRequest, TOTPSetupResponse
from app.services.user_service import UserService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(form: LoginRequest, db: AsyncSession = Depends(get_db)):
    svc = UserService(db)
    user = await svc.get_by_email(form.email)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    # TOTP check for admin/faculty
    if user.totp_enabled:
        if not form.totp_code or not verify_totp(user.totp_secret, form.totp_code):
            raise HTTPException(status_code=401, detail="Invalid or missing TOTP code")

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "institution_id": str(user.institution_id)}
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        role=user.role,
        user_id=str(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    svc = UserService(db)
    user = await svc.get_by_id(payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "institution_id": str(user.institution_id)}
    )
    new_refresh = create_refresh_token(subject=str(user.id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        token_type="bearer",
        role=user.role,
        user_id=str(user.id),
    )


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(db: AsyncSession = Depends(get_db)):
    # In real implementation, get current_user from JWT dependency
    secret = generate_totp_secret()
    # Store secret on user record (pending confirmation)
    return TOTPSetupResponse(secret=secret)
