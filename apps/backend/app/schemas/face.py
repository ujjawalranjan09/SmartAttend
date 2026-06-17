from datetime import datetime
from pydantic import BaseModel


class FaceEnrollmentResponse(BaseModel):
    enrolled: bool
    enrolled_at: datetime | None = None
    model_version: str | None = None