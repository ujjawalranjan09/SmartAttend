from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import qrcode
import io
import secrets
from fastapi.responses import StreamingResponse

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.redis import store_qr_token
from app.core.config import settings
from app.models.user import User
from app.schemas.session import SessionCreate, SessionResponse, QRCodeResponse
from app.services.session_service import SessionService

router = APIRouter()


@router.post("/start", response_model=SessionResponse)
async def start_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Faculty starts a class session — generates initial QR token."""
    svc = SessionService(db)
    session = await svc.start(body)
    # Generate first QR token
    token = secrets.token_urlsafe(32)
    await store_qr_token(str(session.id), token, settings.qr_token_ttl_seconds)
    return SessionResponse.model_validate(session)


@router.post("/{session_id}/end")
async def end_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    svc = SessionService(db)
    await svc.end(session_id)
    return {"message": "Session ended", "session_id": str(session_id)}


@router.post("/{session_id}/qr", response_model=QRCodeResponse)
async def rotate_qr(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate a fresh dynamic QR token (called every 30s by frontend)."""
    svc = SessionService(db)
    session = await svc.get(session_id)
    if not session or session.status != "active":
        raise HTTPException(status_code=404, detail="Active session not found")

    token = secrets.token_urlsafe(32)
    await store_qr_token(str(session_id), token, settings.qr_token_ttl_seconds)
    # Return token + QR image data URL
    qr_data = f"smartattend://attend?session={session_id}&token={token}"
    return QRCodeResponse(session_id=str(session_id), qr_token=token, qr_data=qr_data)


@router.get("/{session_id}/qr.png")
async def qr_image(session_id: UUID, token: str):
    """Serve QR code as PNG image."""
    qr_data = f"smartattend://attend?session={session_id}&token={token}"
    qr = qrcode.make(qr_data)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get("", response_model=list[SessionResponse])
async def list_my_sessions(
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List sessions for the current faculty (or all for admin)."""
    svc = SessionService(db)

    # Use explicit column selection to avoid model/db column drift issues
    from sqlalchemy import select
    from app.models.session import ClassSession

    if current_user.role in ("faculty", "hod"):
        stmt = select(ClassSession).where(ClassSession.faculty_id == current_user.id)
    else:
        stmt = select(ClassSession).order_by(ClassSession.started_at.desc()).limit(50)

    result = await db.execute(stmt)
    sessions = result.scalars().all()

    # Filter by status if provided
    if status:
        sessions = [s for s in sessions if s.status == status]

    return [SessionResponse.model_validate(s) for s in sessions]

# reload trigger 05/26/2026 04:04:08

# reload 05/26/2026 04:04:57
