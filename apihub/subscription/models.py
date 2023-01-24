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
from .schemas import SubscriptionTier, ApplicationCreate, PricingCreate


class Application(Base):
    """
    This class is used to store application data.
    """

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    url = Column(String)
    description = Column(String)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now())
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User")
    subscriptions = relationship("Subscription", back_populates="application")
    pricings = relationship("Pricing", back_populates="application")

    def __str__(self):
        return f"{self.name} || {self.url}"

    def to_schema(self, with_pricing=False) -> ApplicationCreate:
        return ApplicationCreate(
            name=self.name,
            url=self.url,
            description=self.description,
            pricings=[
                PricingCreate(
                    tier=pricing.tier, price=pricing.price, credit=pricing.credit, application=self.name,
                )
                for pricing in self.pricings
            ] if with_pricing else [],
        )


class Pricing(Base):
    """
    This class is used to store subscription pricing data.
    """

    __tablename__ = "pricings"
    __table_args__ = (
        UniqueConstraint(
            "application_id", "tier", name="application_tier_constraint"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.TRIAL)
    price = Column(Integer)
    credit = Column(Integer)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now())

    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    application = relationship("Application", uselist=False, back_populates="pricings")


    def __str__(self):
        return f"{self.application_id} || {self.tier} || {self.price}"


class Subscription(Base):
    """
    This class is used to store subscription data.
    """

    __tablename__ = "subscriptions"
    # __table_args__ = (
    #     UniqueConstraint(
    #         "application_id", "tier", "user_id", name="application_tier_user_constraint"
    #     ),
    # )

    id = Column(Integer, primary_key=True, index=True)
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.TRIAL)
    is_active = Column(Boolean, default=True)
    credit = Column(Integer, default=0)
    balance = Column(Integer, default=0)
    starts_at = Column(DateTime, default=datetime.now())
    expires_at = Column(DateTime)
    recurring = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now())
    # created_by = Column(Integer, ForeignKey("users.id"))
    notes = Column(String)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")

    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    application = relationship("Application", uselist=False, back_populates="subscriptions")

    pricing_id = Column(Integer, ForeignKey("pricings.id"), nullable=False)
    pricing = relationship("Pricing", uselist=False)


    def __str__(self):
        return f"{self.application} || {self.tier} || {self.email}"
