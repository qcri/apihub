from enum import Enum

from pydantic import BaseModel

from .helpers import hash_password


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