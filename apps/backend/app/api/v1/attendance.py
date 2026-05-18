from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.redis import validate_qr_token, rate_limit_check
from app.schemas.attendance import (
    MarkAttendanceRequest,
    AttendanceResponse,
    SessionAttendanceList,
)
from app.services.attendance_service import AttendanceService
from app.services.proxy_service import ProxyDetectionService

router = APIRouter()


@router.post(
    "/mark", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED
)
async def mark_attendance(
    body: MarkAttendanceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Multi-factor attendance marking endpoint.
    Validates: QR token + geo-fence + device fingerprint + (optional) face embedding.
    """
    # Rate limiting: 5 attempts per student per minute
    rate_key = f"attendance_rate:{body.student_id}"
    if not await rate_limit_check(rate_key, limit=5, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many attendance attempts")

    # Validate dynamic QR token
    qr_valid = await validate_qr_token(str(body.session_id), body.qr_token)
    if not qr_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired QR token")

    svc = AttendanceService(db)
    proxy_svc = ProxyDetectionService(db)

    # Check geo-fence
    geo_valid = await svc.validate_geofence(
        session_id=body.session_id,
        lat=body.geo_lat,
        lon=body.geo_lon,
    )
    if not geo_valid:
        raise HTTPException(
            status_code=400, detail="Location outside classroom geo-fence"
        )

    # Create attendance record
    record = await svc.create_record(
        session_id=body.session_id,
        student_id=body.student_id,
        method=body.method,
        geo_lat=body.geo_lat,
        geo_lon=body.geo_lon,
        geo_accuracy_m=body.geo_accuracy_m,
        device_fingerprint=body.device_fingerprint,
        wifi_bssid=body.wifi_bssid,
        face_embedding=body.face_embedding,
        face_confidence=body.face_confidence,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
    )

    # Async proxy detection (fire and forget via Celery)
    await proxy_svc.enqueue_analysis(record.id)

    return AttendanceResponse.model_validate(record)


@router.get("/session/{session_id}", response_model=SessionAttendanceList)
async def get_session_attendance(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    svc = AttendanceService(db)
    records = await svc.get_by_session(session_id)
    return SessionAttendanceList(
        session_id=session_id, records=records, total=len(records)
    )


@router.patch("/{record_id}/override")
async def manual_override(
    record_id: UUID,
    status: str,
    notes: str,
    db: AsyncSession = Depends(get_db),
):
    """Faculty manual override for edge cases."""
    svc = AttendanceService(db)
    record = await svc.override_status(record_id, status, notes)
    return {"message": "Status updated", "record_id": str(record.id)}
