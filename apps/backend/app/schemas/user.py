from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


def _coerce_optional_bool(v: Optional[bool]) -> bool:
    """Treat SQL NULL as False for required bool fields.

    Several boolean columns (e.g. users.is_active, users.totp_enabled) were
    created by early migrations without a server_default, so legacy rows carry
    NULL. Pydantic rejects None for a required bool, which surfaced as a 500 on
    every endpoint returning UserResponse. Coerce None -> False at the schema
    boundary so the API stays robust regardless of column state.
    """
    return bool(v) if v is not None else False


class UserCreate(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    full_name: str = Field(..., min_length=2, max_length=200)
    password: str = Field(..., min_length=8)
    role: UserRole
    institution_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    roll_number: Optional[str] = None
    employee_id: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=200)
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    department_id: Optional[UUID] = None
    roll_number: Optional[str] = None
    employee_id: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    phone: Optional[str]
    full_name: str
    role: UserRole
    institution_id: Optional[UUID]
    department_id: Optional[UUID]
    roll_number: Optional[str]
    employee_id: Optional[str]
    is_active: bool
    totp_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("is_active", "totp_enabled", mode="before")
    @classmethod
    def _none_bool_to_false(cls, v):
        return _coerce_optional_bool(v)


class UserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[UserResponse]


class BulkCreateRequest(BaseModel):
    users: list[UserCreate] = Field(..., min_length=1, max_length=200)


class BulkCreateResponse(BaseModel):
    created: int
    failed: int
    errors: list[dict]
