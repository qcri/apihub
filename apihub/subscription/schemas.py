from datetime import datetime
from typing import Optional, List

from enum import Enum
from pydantic import BaseModel


class ApplicationSchema(BaseModel):
    name: str
    url: str
    description: str


class SubscriptionPricingCreate(BaseModel):
    tier: str
    price: int
    credit: int
    application: str


class SubscriptionPricingCreate2(BaseModel):
    tier: str
    price: int
    credit: int


class ApplicationDetails(ApplicationSchema):
    tier: str
    price: int
    credit: int


class ApplicationCreate(ApplicationSchema):
    pricing: List[SubscriptionPricingCreate2]


class SubscriptionPricingDetails(BaseModel):
    id: int
    tier: str
    price: int
    credit: int
    application: str


class SubscriptionTier(str, Enum):
    TRIAL = "TRIAL"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"


class SubscriptionBase(BaseModel):
    username: str
    application: str
    tier: str


class SubscriptionIn(BaseModel):
    username: str
    application: str
    tier: str
    credit: Optional[int] = 0
    expires_at: Optional[datetime] = None
    recurring: bool = False


class SubscriptionCreate(SubscriptionBase):
    credit: Optional[int] = 0
    starts_at: datetime = datetime.now()
    expires_at: Optional[datetime] = None
    recurring: bool = False
    active: bool = True
    created_by: str
    notes: Optional[str] = None
    application: str


class SubscriptionDetails(SubscriptionCreate):
    created_at: datetime
    balance: int
