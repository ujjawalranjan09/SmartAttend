from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, List
from app.models.attendance import AttendanceMethod, AttendanceStatus


class MarkAttendanceRequest(BaseModel):
    session_id: UUID4
    student_id: UUID4
    qr_token: str
    method: AttendanceMethod = AttendanceMethod.QR_CODE

    # Location
    geo_lat: Optional[float] = None
    geo_lon: Optional[float] = None
    geo_accuracy_m: Optional[float] = None

    # Device
    device_fingerprint: Optional[str] = None
    wifi_bssid: Optional[str] = None
    ble_beacon_id: Optional[str] = None

    # Face (optional layer)
    face_embedding: Optional[List[float]] = None  # 512-dim vector from on-device TF.js
    face_confidence: Optional[float] = None


class AttendanceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID4
    session_id: UUID4
    student_id: UUID4
    status: AttendanceStatus
    method: AttendanceMethod
    marked_at: datetime
    proxy_anomaly_score: Optional[float] = None
    is_verified: bool


class SessionAttendanceList(BaseModel):
    session_id: UUID4
    records: List[AttendanceResponse]
    total: int
