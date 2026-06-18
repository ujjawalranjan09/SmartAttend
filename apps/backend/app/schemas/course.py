from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CourseCreate(BaseModel):
    institution_id: UUID
    department_id: UUID
    faculty_id: UUID | None = None
    subject_id: UUID | None = None
    name: str
    code: str
    semester: int | None = None
    academic_year: str | None = None
    min_attendance_pct: int = 75


class CourseUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    semester: int | None = None
    academic_year: str | None = None
    min_attendance_pct: int | None = None
    faculty_id: UUID | None = None
    department_id: UUID | None = None
    subject_id: UUID | None = None


class CourseResponse(BaseModel):
    id: UUID
    institution_id: UUID
    department_id: UUID
    faculty_id: UUID
    subject_id: UUID | None = None
    name: str
    code: str
    semester: int | None
    academic_year: str | None
    min_attendance_pct: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseListResponse(BaseModel):
    items: list[CourseResponse]
    total: int
    page: int
    page_size: int


class EnrollRequest(BaseModel):
    student_ids: list[UUID]
