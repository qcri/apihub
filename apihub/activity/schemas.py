from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from enum import Enum


class ActivityBase(BaseModel):
    ip: Optional[str] = None
    path: str
    method: str
    user_id: int
    application_id: int
    subscription_id: int
    request_key: Optional[str] = None
    payload: Optional[str] = None
    response: Optional[str] = None


class ActivityCreate(ActivityBase):
    request: str
    username: Optional[str] = None
    tier: str
    status: str
    request_key: Optional[str] = None
    result: Optional[str] = None
    payload: Optional[str] = None
    ip_address: Optional[str] = None
    latency: Optional[float] = None


class ActivityDetails(ActivityCreate):
    created_at: datetime


class ActivityStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    PROCESSED = "PROCESSED"
