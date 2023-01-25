from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from enum import Enum


class ActivityBase(BaseModel):
    ip: Optional[str] = None
    path: str
    method: str
    user_id: int = -1
    request_body: Optional[str] = None
    response_status_code: Optional[str] = None
    response_body: Optional[str] = None


class ActivityDetails(ActivityBase):
    created_at: datetime


class ActivityStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    PROCESSED = "PROCESSED"