from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional
from app.models.session import SessionStatus


class SessionCreate(BaseModel):
    course_id: UUID4
    faculty_id: UUID4
    timetable_slot_id: Optional[UUID4] = None
    is_online: bool = False
    meeting_url: Optional[str] = None
    qr_rotation_interval_sec: int = 30


class SessionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID4
    course_id: UUID4
    faculty_id: UUID4
    status: SessionStatus
    started_at: Optional[datetime]
    is_online: bool
    meeting_url: Optional[str]


class QRCodeResponse(BaseModel):
    session_id: str
    qr_token: str
    qr_data: str  # Deep link data encoded in QR
    expires_in_seconds: int = 120
