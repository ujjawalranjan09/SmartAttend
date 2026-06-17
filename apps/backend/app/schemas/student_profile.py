from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# ─── Profile Schemas ──────────────────────────────────────────────────────────


class StudentProfileCreate(BaseModel):
    interests: list[str] = []
    strengths: list[str] = []
    career_goals: list[str] = []
    preferred_study_style: str | None = None
    daily_study_hours_target: int = 2


class StudentProfileUpdate(BaseModel):
    interests: list[str] | None = None
    strengths: list[str] | None = None
    career_goals: list[str] | None = None
    preferred_study_style: str | None = None
    daily_study_hours_target: int | None = None


class StudentProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    interests: list[str]
    strengths: list[str]
    career_goals: list[str]
    preferred_study_style: str | None
    daily_study_hours_target: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Goal Schemas ─────────────────────────────────────────────────────────────


class MilestoneItem(BaseModel):
    title: str
    completed: bool = False


class StudentGoalCreate(BaseModel):
    title: str
    description: str | None = None
    category: str  # academic | career | skill | project | exam_prep
    priority: str = "medium"  # low | medium | high
    target_date: date | None = None
    estimated_hours: int | None = None
    milestones: list[MilestoneItem] = []


class StudentGoalUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    priority: str | None = None
    target_date: date | None = None
    estimated_hours: int | None = None
    status: str | None = None  # active | completed | paused | abandoned
    milestones: list[MilestoneItem] | None = None


class StudentGoalResponse(BaseModel):
    id: UUID
    student_id: UUID
    title: str
    description: str | None
    category: str
    priority: str
    target_date: date | None
    estimated_hours: int | None
    completed_hours: int
    status: str
    milestones: list[MilestoneItem]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalProgressUpdate(BaseModel):
    completed_hours: int
    milestone_index: int | None = None  # mark a specific milestone done


class StudentGoalsListResponse(BaseModel):
    items: list[StudentGoalResponse]
    total: int