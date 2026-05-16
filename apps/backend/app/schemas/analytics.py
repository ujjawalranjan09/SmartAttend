from pydantic import BaseModel, UUID4
from datetime import date
from typing import List, Optional


class AttendanceTrend(BaseModel):
    date: date
    attended: int
    total: int
    percentage: float
    forecast: Optional[float] = None  # Prophet prediction


class StudentAnalyticsResponse(BaseModel):
    student_id: UUID4
    full_name: str
    overall_attendance_pct: float
    courses: List[dict]  # Per-course breakdown
    trend: List[AttendanceTrend]
    proxy_incidents: int
    at_risk: bool
    forecast_7d_pct: Optional[float] = None


class CourseAnalyticsResponse(BaseModel):
    course_id: UUID4
    course_name: str
    total_sessions: int
    avg_attendance_pct: float
    engagement_score: float  # Composite metric
    at_risk_students: int
    proxy_incidents: int
    trend: List[AttendanceTrend]


class AtRiskStudent(BaseModel):
    student_id: UUID4
    full_name: str
    roll_number: Optional[str]
    current_attendance_pct: float
    min_required_pct: float
    courses_at_risk: List[str]
    last_attended: Optional[date]
