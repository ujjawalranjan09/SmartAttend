from uuid import UUID
from datetime import datetime, time
from typing import Optional
from pydantic import BaseModel, ConfigDict


# ── Batch ─────────────────────────────────────────────────────────────────────

class BatchCreate(BaseModel):
    institution_id: UUID
    department_id: Optional[UUID] = None
    name: str
    code: str
    academic_year: Optional[str] = None
    semester: Optional[int] = None


class BatchUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    department_id: Optional[UUID] = None
    academic_year: Optional[str] = None
    semester: Optional[int] = None
    is_active: Optional[bool] = None


class BatchResponse(BaseModel):
    id: UUID
    institution_id: UUID
    department_id: Optional[UUID]
    name: str
    code: str
    academic_year: Optional[str]
    semester: Optional[int]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchListResponse(BaseModel):
    items: list[BatchResponse]
    total: int


# ── Batch schedule (weekly recurring assignment) ──────────────────────────────

class BatchScheduleCreate(BaseModel):
    batch_id: UUID
    faculty_id: UUID
    subject_id: UUID
    day_of_week: int  # 0=Mon..6=Sun
    start_time: time
    end_time: time
    room: Optional[str] = None


class BatchScheduleUpdate(BaseModel):
    faculty_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    day_of_week: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    room: Optional[str] = None
    is_active: Optional[bool] = None


class BatchScheduleResponse(BaseModel):
    id: UUID
    institution_id: UUID
    batch_id: UUID
    faculty_id: UUID
    subject_id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    room: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchScheduleListResponse(BaseModel):
    items: list[BatchScheduleResponse]
    total: int


# ── Members (students assigned to a batch) ────────────────────────────────────

class BatchMemberIds(BaseModel):
    user_ids: list[UUID]
