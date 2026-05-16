from uuid import UUID
from datetime import datetime, date
from typing import Optional, Literal
from pydantic import BaseModel


class ReportRequest(BaseModel):
    institution_id: UUID
    report_type: Literal["student", "course", "department", "institution", "proxy"]
    from_date: date
    to_date: date
    course_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    student_id: Optional[UUID] = None
    format: Literal["csv", "pdf", "json"] = "pdf"
    include_proxy_incidents: bool = True
    min_attendance_pct: Optional[float] = None


class ReportJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "done", "failed"]
    message: str
    download_url: Optional[str] = None
    created_at: datetime


class AttendanceRow(BaseModel):
    student_id: UUID
    student_name: str
    roll_number: Optional[str]
    course_name: str
    total_sessions: int
    attended: int
    attendance_pct: float
    proxy_incidents: int
    status: Literal["safe", "at_risk", "detained"]
