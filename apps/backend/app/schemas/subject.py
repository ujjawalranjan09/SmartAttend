from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SubjectCreate(BaseModel):
    institution_id: UUID
    department_id: Optional[UUID] = None
    name: str
    code: str


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    department_id: Optional[UUID] = None


class SubjectResponse(BaseModel):
    id: UUID
    institution_id: UUID
    department_id: Optional[UUID]
    name: str
    code: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubjectListResponse(BaseModel):
    items: list[SubjectResponse]
    total: int
