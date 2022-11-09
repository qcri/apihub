from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Float, Enum

from ..common.db_session import Base, db_context
from ..subscription.schemas import SubscriptionTier
from .schemas import ActivityStatus, ActivityCreate


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

    @staticmethod
    def create_activity_helper(**kwargs):
        from .queries import ActivityQuery

        with db_context() as session:
            ActivityQuery(session).create_activity(
                ActivityCreate(
                    request=kwargs.get("request"),
                    username=kwargs.get("username"),
                    tier=kwargs.get("tier"),
                    status=kwargs.get("status"),
                    request_key=kwargs.get("request_key"),
                    result=kwargs.get("result"),
                    payload=kwargs.get("payload"),
                    ip_address=kwargs.get("ip_address"),
                    latency=kwargs.get("latency"),
                )
            )

    def __str__(self):
        return f"{self.request} || {self.username}"
