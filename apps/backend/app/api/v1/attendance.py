from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.redis import validate_qr_token, rate_limit_check
from app.models.attendance import AttendanceRecord, AttendanceMethod
from app.models.user import User
from app.models.session import ClassSession
from app.models.course import Course, Enrollment
from app.schemas.attendance import MarkAttendanceRequest, AttendanceResponse, SessionAttendanceList
from app.services.attendance_service import AttendanceService
from app.services.proxy_service import ProxyDetectionService
from app.websocket.handlers import broadcast_to_session

router = APIRouter()


@router.post("/mark", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def mark_attendance(
    body: MarkAttendanceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Multi-factor attendance marking endpoint.
    Validates: QR token + geo-fence + device fingerprint + (optional) face embedding.
    """
    # Rate limiting: 5 attempts per student per minute
    rate_key = f"attendance_rate:{current_user.id}"
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
        raise HTTPException(status_code=400, detail="Location outside classroom geo-fence")

    # Create attendance record
    record = await svc.create_record(
        session_id=body.session_id,
        student_id=current_user.id,
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

    # Broadcast to all WebSocket listeners (display screen + faculty live view)
    await _broadcast_attendance_update(db, str(body.session_id), record, current_user)

    return AttendanceResponse.model_validate(record)


async def _broadcast_attendance_update(
    db: AsyncSession, session_id: str, record: AttendanceRecord, student: User
):
    """Broadcast attendance event to all WebSocket listeners for this session."""
    from sqlalchemy import func, select

    # Get present count for this session
    present_result = await db.execute(
        select(func.count(AttendanceRecord.id)).where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.status == "present",
        )
    )
    present_count = present_result.scalar() or 0

    # Total enrolled comes from the Enrollment table (NOT attendance records)
    # — otherwise present_percentage is misleading (1 student marks -> 100%).
    course_result = await db.execute(
        select(ClassSession.course_id).where(ClassSession.id == session_id)
    )
    course_id = course_result.scalar_one_or_none()
    if course_id:
        enrolled_result = await db.execute(
            select(func.count(Enrollment.id)).where(Enrollment.course_id == course_id)
        )
        total_enrolled = enrolled_result.scalar() or 0
    else:
        total_enrolled = 0

    broadcast_payload = {
        "event": "attendance_marked",
        "session_id": session_id,
        "student_name": student.full_name,
        "roll_number": student.roll_number or "N/A",
        "marked_at": record.marked_at.isoformat() if record.marked_at else datetime.utcnow().isoformat(),
        "status": record.status.value if hasattr(record.status, "value") else str(record.status),
        "method": record.method.value if hasattr(record.method, "value") else str(record.method),
        "present_count": present_count,
        "total_enrolled": total_enrolled,
        "present_percentage": round((present_count / total_enrolled * 100), 1) if total_enrolled > 0 else 0.0,
    }
    await broadcast_to_session(session_id, broadcast_payload)


@router.get("/session/{session_id}", response_model=SessionAttendanceList)
async def get_session_attendance(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    svc = AttendanceService(db)
    records = await svc.get_by_session(session_id)
    return SessionAttendanceList(session_id=session_id, records=records, total=len(records))


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


@router.get("", response_model=list[dict])
async def list_attendance_records(
    limit: int = Query(100, le=500),
    student_id: Optional[UUID] = Query(None),
    session_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recent attendance records (for faculty dashboard)."""
    stmt = (
        select(
            AttendanceRecord.id,
            AttendanceRecord.session_id,
            AttendanceRecord.student_id,
            AttendanceRecord.status,
            AttendanceRecord.method,
            AttendanceRecord.marked_at,
            AttendanceRecord.face_confidence,
            User.full_name.label("student_name"),
            Course.name.label("course_name"),
        )
        .join(User, AttendanceRecord.student_id == User.id, isouter=True)
        .join(ClassSession, AttendanceRecord.session_id == ClassSession.id, isouter=True)
        .join(Course, ClassSession.course_id == Course.id, isouter=True)
        .order_by(AttendanceRecord.marked_at.desc())
        .limit(limit)
    )

    if student_id:
        stmt = stmt.where(AttendanceRecord.student_id == student_id)
    if session_id:
        stmt = stmt.where(AttendanceRecord.session_id == session_id)

    result = await db.execute(stmt)
    rows = result.all()

    records = []
    for row in rows:
        (rec_id, sess_id, stud_id, status, method, marked_at, face_conf,
         student_name, course_name) = row

        records.append({
            "id": str(rec_id),
            "session_id": str(sess_id),
            "student_id": str(stud_id),
            "student_name": student_name or "Unknown Student",
            "course_name": course_name or "Unknown Course",
            "status": status.value if hasattr(status, 'value') else str(status),
            "method": method.value if hasattr(method, 'value') else str(method),
            "marked_at": marked_at.isoformat() if marked_at else None,
            "face_confidence": face_conf,
            "proxy_risk_score": None,
        })

    return records

# reload 05/26/2026 04:04:39

# reload 05/26/2026 04:05:15
