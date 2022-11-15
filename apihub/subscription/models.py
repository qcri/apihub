from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from ..common.db_session import Base
from .schemas import SubscriptionTier


class Application(Base):
    """
    This class is used to store application data.
    """

    __tablename__ = "application"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    url = Column(String)
    description = Column(String)

    subscriptions = relationship("Subscription", backref="app")
    subscriptions_pricing = relationship("SubscriptionPricing", backref="app")

    def __str__(self):
        return f"{self.name} || {self.url}"


class SubscriptionPricing(Base):
    """
    This class is used to store subscription pricing data.
    """

    __tablename__ = "subscription_pricing"
    __table_args__ = (UniqueConstraint("application", "tier", name="application_tier"),)

    id = Column(Integer, primary_key=True, index=True)
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.TRIAL)
    price = Column(Integer)
    credit = Column(Integer)

    application = Column(String, ForeignKey("application.name"), nullable=False)

    def __str__(self):
        return f"{self.application} || {self.tier} || {self.price}"


class Subscription(Base):
    """
    This class is used to store subscription data.
    """

    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "application", "tier", "username", name="application_tier_username"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.TRIAL)
    active = Column(Boolean, default=True)
    credit = Column(Integer, default=0)
    balance = Column(Integer, default=0)
    starts_at = Column(DateTime, default=datetime.now())
    expires_at = Column(DateTime)
    recurring = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now())
    created_by = Column(String)
    notes = Column(String)

    username = Column(String, ForeignKey("users.username"), nullable=False)
    user = relationship("User", back_populates="subscriptions")

    application = Column(String, ForeignKey("application.name"), nullable=False)

    def __str__(self):
        return f"{self.application} || {self.tier} || {self.username}"
