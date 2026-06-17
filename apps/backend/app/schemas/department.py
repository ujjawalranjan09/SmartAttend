from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class DepartmentCreate(BaseModel):
    institution_id: UUID
    name: str
    code: str


class DepartmentUpdate(BaseModel):
    name: str | None = None
    code: str | None = None


class DepartmentResponse(BaseModel):
    id: UUID
    institution_id: UUID
    name: str
    code: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DepartmentListResponse(BaseModel):
    items: list[DepartmentResponse]
    total: int
