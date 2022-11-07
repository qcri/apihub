from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Float, Enum

from apihub.common.db_session import Base
from ..subscription.schemas import SubscriptionTier
from .schemas import ActivityStatus


class Activity(Base):
    """
    This class is used to store activity data.
    """

    __tablename__ = "activity"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.now())
    request = Column(String)
    username = Column(String)
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.TRIAL)
    status = Column(Enum(ActivityStatus), default=ActivityStatus.ACCEPTED)
    request_key = Column(String)
    result = Column(String)
    payload = Column(String)
    ip_address = Column(String)
    latency = Column(Float)

    def __str__(self):
        return f"{self.request} || {self.username}"
