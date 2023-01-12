from datetime import datetime
from typing import Optional, List

from enum import Enum
from pydantic import BaseModel


class SubscriptionTier(str, Enum):
    TRIAL = "TRIAL"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"

class SubscriptionPricingBase(BaseModel):
    tier: SubscriptionTier
    price: int
    credit: int


class SubscriptionPricingCreate(SubscriptionPricingBase):
    application: str


class SubscriptionPricingDetails(SubscriptionPricingCreate):
    id: int


class ApplicationBase(BaseModel):
    name: str
    url: str
    description: str


class ApplicationCreate(ApplicationBase):
    pricing: List[SubscriptionPricingBase]


class ApplicationCreateWithOwner(ApplicationCreate):
    owner: str


class SubscriptionBase(BaseModel):
    username: str
    application: str
    tier: SubscriptionTier


class SubscriptionIn(SubscriptionBase):
    expires_at: Optional[datetime] = None
    recurring: bool = False


class SubscriptionCreate(SubscriptionIn):
    credit: Optional[int] = 0
    starts_at: datetime = datetime.now()
    active: bool = True
    created_by: str
    notes: Optional[str] = None
    application: str


class SubscriptionDetails(SubscriptionCreate):
    created_at: datetime
    balance: int
