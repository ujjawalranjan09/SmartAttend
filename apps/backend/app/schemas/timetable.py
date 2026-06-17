from uuid import UUID
from datetime import time
from pydantic import BaseModel, ConfigDict


class SlotCreate(BaseModel):
    course_id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    room: str | None = None
    building: str | None = None
    geo_lat: float | None = None
    geo_lon: float | None = None
    geo_radius_m: int | None = None


class SlotUpdate(BaseModel):
    course_id: UUID | None = None
    day_of_week: int | None = None
    start_time: time | None = None
    end_time: time | None = None
    room: str | None = None
    building: str | None = None
    geo_lat: float | None = None
    geo_lon: float | None = None
    geo_radius_m: int | None = None


class SlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    course_id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    room: str | None
    building: str | None
    geo_lat: float | None
    geo_lon: float | None
    geo_radius_m: int | None


class DaySlot(BaseModel):
    date: str
    day_name: str
    slots: list[dict]


class WeeklyViewResponse(BaseModel):
    days: list[DaySlot]
