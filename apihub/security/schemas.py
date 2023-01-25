import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from fastapi_jwt_auth import AuthJWT

from .helpers import hash_password


class SecurityToken(BaseModel):
    email: str
    role: str
    name: str
    user_id: int
    expires_days: Optional[int] = None
    access_token: Optional[str] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.access_token is None:
            self.access_token = self.to_token()

    def to_token(self):
        Authorize = AuthJWT()
        expires_time = datetime.timedelta(days=self.expires_days)
        access_token = Authorize.create_access_token(
            subject=self.email,
            user_claims={
                "role": self.role, "name": self.name, "user_id": self.user_id,
            },
            expires_time=expires_time,
        )
        return access_token

    @classmethod
    def from_token(cls, Authorize: AuthJWT):
        email = Authorize.get_jwt_subject()
        claims = Authorize.get_raw_jwt()
        return cls(
            email=email,
            role=claims["role"],
            name=claims["name"],
            user_id=claims["user_id"],
            expires_days=0,
        )


class UserType(str, Enum):
    USER = "user"
    PUBLISHER = "publisher"
    APP = "app"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: str
    name: str
    role: UserType

    @property
    def is_admin(self) -> bool:
        return self.role == UserType.ADMIN

    @property
    def is_publisher(self) -> bool:
        return self.role == UserType.PUBLISHER

    @property
    def is_user(self) -> bool:
        return self.role == UserType.USER

    @property
    def is_app(self) -> bool:
        return self.role == UserType.APP


class UserBaseWithId(UserBase):
    id: int


class UserRegister(BaseModel):
    name: str
    email: str
    password: str


class UserCreate(UserBase):
    password: str

    def make_user(self):
        """
        Make a User object from UserCreate object.
        :return:
        """
        salt, hashed_password = hash_password(self.password)
        return UserCreateHashed(
            name=self.name,
            email=self.email,
            salt=salt,
            hashed_password=hashed_password,
            role=self.role,
        )


class UserCreateHashed(UserBase):
    salt: str
    hashed_password: str


class UserSession(UserBase):
    id: int
    salt: str
    hashed_password: str


class User(UserSession):
    pass


class ProfileBase(BaseModel):
    first_name: str
    last_name: str
    bio: Optional[str]
    url: Optional[str]
    avatar: Optional[str]