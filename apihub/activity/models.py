from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Float, Enum

from ..common.db_session import Base
from ..subscription.schemas import SubscriptionTier
from .schemas import ActivityStatus


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.now())
    ip = Column(String)
    path = Column(String)
    method = Column(String)
    user_id = Column(Integer, default=-1)
    request_body = Column(String)
    response_status_code = Column(String)
    response_body = Column(String)

    def __str__(self):
        return f"{self.ip} || {self.path} || {self.method} || {self.user_id}"