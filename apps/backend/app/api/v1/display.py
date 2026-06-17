"""
Display API — Classroom Display Screen endpoints.
Provides short-lived display tokens and read-only session attendance data.
"""

import uuid
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from jose import jwt, JWTError
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_faculty
from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.models.session import ClassSession
from app.models.course import Course
from app.models.user import User

router = APIRouter()

# Display token expiry in hours
DISPLAY_TOKEN_TTL_HOURS = 4


# ─── Token generation ─────────────────────────────────────────────────────────


def _create_display_token(session_id: UUID) -> str:
    """Create a short-lived JWT scoped to a specific session."""
    payload = {
        "sub": str(session_id),
        "exp": datetime.utcnow() + timedelta(hours=DISPLAY_TOKEN_TTL_HOURS),
        "type": "display",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def _validate_display_token(token: str) -> UUID:
    """Validate a display token and return the session_id. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        if payload.get("type") != "display":
            raise HTTPException(status_code=403, detail="Invalid token type")
        return UUID(payload["sub"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired display token")


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/sessions/{session_id}/display-token")
async def generate_display_token(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_faculty),
):
    """
    Generate a short-lived display token for a session.
    Faculty only. Token expires in 4 hours.
    """
    # Verify session exists and belongs to this faculty
    result = await db.execute(
        select(ClassSession).where(
            ClassSession.id == session_id,
            ClassSession.faculty_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found or not yours")

    display_token = _create_display_token(session_id)
    return {"display_token": display_token}


@router.get("/display/session/{session_id}")
async def get_display_session(
    session_id: UUID,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Read-only display endpoint. Validates display token.
    Returns course info, attendance counts, and list of present students.
    No authentication required — token is the auth mechanism.
    """
    # Validate token
    token_session_id = _validate_display_token(token)
    if token_session_id != session_id:
        raise HTTPException(status_code=403, detail="Token not valid for this session")

    # Get session + course info
    result = await db.execute(
        select(ClassSession, Course)
        .join(Course, ClassSession.course_id == Course.id)
        .where(ClassSession.id == session_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    session_obj, course = row

    # Get attendance counts
    att_result = await db.execute(
        select(
            func.count(AttendanceRecord.id).label("total"),
            func.count(
                func.nullif(
                    AttendanceRecord.status != AttendanceStatus.PRESENT.value, True
                )
            ).label("present"),
        ).where(AttendanceRecord.session_id == session_id)
    )
    att_row = att_result.one()
    total_enrolled = att_row.total or 0
    present_count = att_row.present or 0

    # Also count total enrolled students (from course enrollments)
    from app.models.course import Enrollment
    enrolled_result = await db.execute(
        select(func.count(Enrollment.id)).where(Enrollment.course_id == course.id)
    )
    total_enrolled = enrolled_result.scalar() or total_enrolled

    # Get list of present students
    present_result = await db.execute(
        select(User.full_name, User.roll_number, AttendanceRecord.marked_at)
        .join(User, AttendanceRecord.student_id == User.id)
        .where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.status == AttendanceStatus.PRESENT.value,
        )
        .order_by(AttendanceRecord.marked_at.asc())
    )
    present_students = [
        {
            "student_name": row[0],
            "roll_number": row[1] or "N/A",
            "marked_at": row[2].isoformat() if row[2] else None,
        }
        for row in present_result.all()
    ]

    present_pct = round((present_count / total_enrolled * 100), 1) if total_enrolled > 0 else 0.0

    return {
        "course_name": course.name,
        "course_code": course.code,
        "start_time": session_obj.started_at.isoformat() if session_obj.started_at else None,
        "room": None,  # Would come from timetable slot if needed
        "total_enrolled": total_enrolled,
        "present_count": present_count,
        "absent_count": total_enrolled - present_count,
        "present_percentage": present_pct,
        "present_students": present_students,
        "session_status": session_obj.status.value if hasattr(session_obj.status, 'value') else str(session_obj.status),
    }