from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
)

from ..common.db_session import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    application = Column(String, index=True)
    limit = Column(Integer)
    starts_at = Column(DateTime, default=datetime.now())
    expires_at = Column(DateTime)
    recurring = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now())
    created_by = Column(String)
    notes = Column(String)


class Usage(Base):
    __tablename__ = "usages"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    application = Column(String, index=True)
    usage = Column(Integer, default=0)
    starts_at = Column(DateTime)
    expires_at = Column(DateTime)
