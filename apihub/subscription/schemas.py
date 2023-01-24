from datetime import datetime
from typing import Optional, List

from enum import Enum
from pydantic import BaseModel


class SubscriptionTier(str, Enum):
    TRIAL = "TRIAL"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"

class PricingBase(BaseModel):
    tier: SubscriptionTier
    price: int
    credit: int


class PricingCreate(PricingBase):
    application: str


class PricingDetails(PricingCreate):
    id: int


class ApplicationBase(BaseModel):
    name: str
    url: str
    description: str


class ApplicationCreate(ApplicationBase):
    pricings: List[PricingBase]


class ApplicationCreateWithOwner(ApplicationCreate):
    user_id: int


class ApplicationDetailsWithId(ApplicationCreateWithOwner):
    id: int


class SubscriptionBase(BaseModel):
    user_id: int
    application_id: int
    tier: SubscriptionTier


class SubscriptionIn(SubscriptionBase):
    pricing_id: int
    expires_at: Optional[datetime] = None
    recurring: bool = False


class SubscriptionCreate(SubscriptionIn):
    credit: Optional[int] = 0
    starts_at: datetime = datetime.now()
    notes: Optional[str] = None


class SubscriptionDetails(SubscriptionCreate):
    id: int
    created_at: datetime
    balance: int