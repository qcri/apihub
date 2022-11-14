from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Enum,
    Float,
)
from sqlalchemy.orm import relationship

from ..common.db_session import Base
from .schemas import SubscriptionTier


class Application(Base):
    """
    This class is used to store application data.
    """

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    url = Column(String)

    subscription_pricing = relationship(
        "SubscriptionPricing", back_populates="application"
    )

    def __str__(self):
        return f"{self.name} || {self.url}"


class SubscriptionPricing(Base):
    """
    This class is used to store subscription pricing data.
    """

    __tablename__ = "subscription_pricing"

    id = Column(Integer, primary_key=True, index=True)
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.TRIAL)
    price = Column(Float)
    credit = Column(Float)

    application = Column(String, ForeignKey("applications.name"), nullable=False)
    application_instance = relationship(
        "Application", back_populates="subscription_pricing"
    )

    subscriptions = relationship("Subscription", back_populates="application")

    def __str__(self):
        return f"{self.application} || {self.tier} || {self.price}"


class Subscription(Base):
    """
    This class is used to store subscription data.
    """

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    # duplicate tier to make it easier to query.
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.TRIAL)
    active = Column(Boolean, default=True)
    # keep credit in as it's to avoid querying SubscriptionPricing too often.
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

    application = Column(
        String, ForeignKey("subscription_pricing.application"), nullable=False
    )
    subscription_pricing = relationship(
        "SubscriptionPricing", back_populates="subscription_pricing"
    )

    def __str__(self):
        return f"{self.application} || {self.tier} || {self.username}"
