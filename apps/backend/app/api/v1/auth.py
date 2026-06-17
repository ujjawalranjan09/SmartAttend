import hashlib
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, oauth2_scheme_without_error
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_totp,
    generate_totp_secret,
    generate_secure_token,
)
from app.models.password_reset import PasswordReset
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    LoginRequest,
    RefreshRequest,
    TOTPSetupResponse,
    RegisterRequest,
    VerifyRegistrationRequest,
    UserRegistrationResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
)
from app.schemas.user import UserCreate
from app.services.email_service import send_email, send_templated_email
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

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
    if not user.is_verified:
        raise HTTPException(
            status_code=403, detail="Email not verified. Please check your inbox."
        )

    # TOTP check for admin/faculty
    if user.totp_enabled:
        if not form.totp_code or not verify_totp(user.totp_secret, form.totp_code):
            raise HTTPException(status_code=401, detail="Invalid or missing TOTP code")

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "institution_id": str(user.institution_id)},
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
        extra_claims={"role": user.role, "institution_id": str(user.institution_id)},
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
async def setup_totp(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    secret = generate_totp_secret()
    current_user.totp_secret = secret
    await db.commit()
    return TOTPSetupResponse(secret=secret)


@router.post(
    "/register",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    svc = UserService(db)
    existing = await svc.get_by_email(body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_data = UserCreate(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        role=body.role,
        institution_id=body.institution_id,
    )
    user = await svc.create(user_data)

    # Deactivate until email is verified
    user.is_active = False
    user.is_verified = False
    await db.commit()

    raw_token = generate_secure_token()
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    pr = PasswordReset(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(pr)
    await db.commit()
    logger.info("Verification token for %s: %s", user.email, raw_token)

    # Send verification email (2.9)
    try:
        await send_templated_email(
            user.email,
            "verification",
            {
                "name": user.full_name,
                "token": raw_token,
                "verify_url": f"/verify?token={raw_token}",
            },
        )
    except Exception as e:
        logger.warning("Failed to send verification email: %s", e)

    return UserRegistrationResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )


@router.post("/verify-registration")
async def verify_registration(
    body: VerifyRegistrationRequest, db: AsyncSession = Depends(get_db)
):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    result = await db.execute(
        select(PasswordReset).where(
            PasswordReset.token_hash == token_hash,
            PasswordReset.used == False,
            PasswordReset.expires_at > datetime.utcnow(),
        )
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    pr.user.is_active = True
    pr.user.is_verified = True
    pr.used = True
    await db.commit()
    return {"detail": "Email verified successfully"}


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    svc = UserService(db)
    user = await svc.get_by_email(body.email)

    if user:
        raw_token = generate_secure_token()
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        pr = PasswordReset(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(pr)
        await db.commit()
        # Send templated email (2.9)
        try:
            await send_templated_email(
                user.email,
                "password_reset",
                {
                    "name": user.full_name,
                    "token": raw_token,
                    "reset_url": f"/reset-password?token={raw_token}",
                },
            )
        except Exception as e:
            logger.warning("Failed to send password reset email: %s", e)
            # Fallback to plain text
            await send_email(user.email, "Password Reset", f"Token: {raw_token}")

    return {"detail": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    result = await db.execute(
        select(PasswordReset).where(
            PasswordReset.token_hash == token_hash,
            PasswordReset.used == False,
            PasswordReset.expires_at > datetime.utcnow(),
        )
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    pr.user.hashed_password = hash_password(body.new_password)
    pr.used = True
    await db.commit()
    return {"detail": "Password reset successfully"}


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.hashed_password = hash_password(body.new_password)
    await db.commit()
    return {"detail": "Password changed successfully"}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Return current logged-in user (used by frontend after login)."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "institution_id": str(current_user.institution_id)
        if current_user.institution_id
        else None,
        "department_id": str(current_user.department_id)
        if current_user.department_id
        else None,
        "is_active": current_user.is_active,
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme_without_error),
):
    """Logout by blacklisting the current access token."""
    if not token:
        return {"detail": "No token to blacklist"}

    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            ttl = max(1, int(exp) - int(datetime.utcnow().timestamp()))
            from app.core.redis import blacklist_token

            await blacklist_token(jti, ttl)
    except Exception as e:
        logger.warning(f"Logout blacklist failed: {e}")

    return {"detail": "Logged out successfully"}


@router.post("/data-export")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all user data (right to data portability — DPDP compliance)."""
    from app.models.face import FaceEmbedding
    from app.models.attendance import AttendanceRecord
    from app.models.notification import Notification

    # Basic info
    data = {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "phone": current_user.phone,
            "institution_id": str(current_user.institution_id)
            if current_user.institution_id
            else None,
            "roll_number": current_user.roll_number,
            "created_at": current_user.created_at.isoformat()
            if current_user.created_at
            else None,
        }
    }

    # Face enrollment
    try:
        face_result = await db.execute(
            select(FaceEmbedding).where(FaceEmbedding.user_id == current_user.id)
        )
        face = face_result.scalar_one_or_none()
        if face:
            data["face_enrollment"] = {
                "enrolled_at": face.enrolled_at.isoformat(),
                "model_version": face.model_version,
            }
    except Exception:
        pass  # face_embeddings table may not exist in test DB

    # Attendance records
    att_result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.student_id == current_user.id
        ).limit(100)
    )
    records = att_result.scalars().all()
    data["attendance_records"] = [
        {
            "session_id": str(r.session_id),
            "status": r.status,
            "method": r.method,
            "marked_at": r.marked_at.isoformat() if r.marked_at else None,
        }
        for r in records
    ]

    # Notifications
    notif_result = await db.execute(
        select(Notification).where(
            Notification.user_id == current_user.id
        ).limit(50)
    )
    notifications = notif_result.scalars().all()
    data["notifications"] = [
        {
            "title": n.title,
            "body": n.body,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]

    return data


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete account (soft-delete) and anonymize personal data — DPDP compliance."""
    import hashlib

    user = current_user
    user.is_active = False
    user.full_name = "Deleted User"
    user.email = hashlib.sha256(user.email.encode()).hexdigest() + "@deleted.local"
    user.phone = None
    user.roll_number = None
    user.hashed_password = ""

    # Soft-delete face embeddings
    try:
        from app.models.face import FaceEmbedding

        face_result = await db.execute(
            select(FaceEmbedding).where(FaceEmbedding.user_id == user.id)
        )
        face = face_result.scalar_one_or_none()
        if face:
            face.is_active = False
    except Exception:
        pass  # face_embeddings table may not exist

    await db.commit()


# reload trigger 05/26/2026 03:48:23
