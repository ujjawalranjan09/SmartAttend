from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.alert import AlertType, AlertSeverity


class AlertResponse(BaseModel):
    id: UUID
    institution_id: UUID
    student_id: Optional[UUID]
    course_id: Optional[UUID]
    session_id: Optional[UUID]
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    anomaly_score: Optional[float]
    is_resolved: bool
    resolved_by_id: Optional[UUID]
    resolved_at: Optional[datetime]
    created_at: datetime
    student_name: Optional[str] = None
    course_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
