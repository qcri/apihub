from datetime import datetime
from typing import Optional, List

from enum import Enum
from pydantic import BaseModel

from fastapi_jwt_auth import AuthJWT


class SubscriptionToken(BaseModel):
    user_id: int
    role: str
    subscription_id: int
    application_id: int
    email: str
    tier: str
    application: str
    access_token: Optional[str] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.access_token = self.to_token()

    def to_token(self):
        Authorize = AuthJWT()
        access_token = Authorize.create_access_token(
            subject=self.email,
            user_claims={
                "role": self.role,
                "user_id": self.user_id,
                "subscription_id": self.subscription_id,
                "application_id": self.application_id,
                "tier": self.tier,
                "application": self.application,
            },
        )
        return access_token

    @classmethod
    def from_token(cls, Authorize: AuthJWT):
        email = Authorize.get_jwt_subject()
        claims = Authorize.get_raw_jwt()
        return cls(
            email=email,
            role=claims["role"],
            user_id=claims["user_id"],
            subscription_id=claims["subscription_id"],
            application_id=claims["application_id"],
            tier=claims["tier"],
            application=claims["application"],
        )


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