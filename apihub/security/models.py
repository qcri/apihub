from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
    Enum,
)
from .schemas import UserType

from ..common.db_session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    salt = Column(String)
    hashed_password = Column(String)
    role = Column(Enum(UserType))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now())
