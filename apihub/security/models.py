from datetime import datetime

from sqlalchemy.orm import relationship
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
)

from .schemas import UserType
from ..common.db_session import Base


class User(Base):
    """
    This class is used to store user data.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, unique=True, nullable=False)
    name = Column(String, nullable=False)
    salt = Column(String)
    hashed_password = Column(String)
    role = Column(Enum(UserType), default=UserType.USER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now())

    profile = relationship("Profile", uselist=False, back_populates="user")

    def __str__(self):
        return f"{self.email} || {self.role} || {self.is_active}"

    


class Profile(Base):
    """
    This class is used to store user profile data.
    """
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    bio = Column(String)
    url = Column(String)
    avatar = Column(String)

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", cascade = "all,delete", back_populates="profile")

    def __str__(self):
        return f"{self.user_id} || {self.name}"