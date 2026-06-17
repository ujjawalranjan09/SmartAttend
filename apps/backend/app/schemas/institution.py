from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class InstitutionCreate(BaseModel):
    name: str
    short_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"


class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    is_active: Optional[bool] = None


class InstitutionResponse(BaseModel):
    id: UUID
    name: str
    short_name: str
    city: Optional[str]
    state: Optional[str]
    country: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstitutionListResponse(BaseModel):
    items: list[InstitutionResponse]
    total: int
    page: int
    page_size: int
