import sys

from pydantic import BaseSettings

from apihub.common.db_session import db_context, Base, DB_ENGINE
from apihub.common.redis_session import redis_context
from apihub.security.schemas import UserCreate, UserType
from apihub.security.queries import UserQuery
from apihub.usage.helpers import copy_yesterday_usage
from apihub.security.models import *  # noqa
from apihub.subscription.models import *  # noqa
from apihub.usage.models import *  # noqa


class SuperUser(BaseSettings):
    username: str
    password: str
    email: str

    def as_usercreate(self):
        return UserCreate(
            username=self.username,
            password=self.password,
            email=self.email,
            role=UserType.ADMIN,
        )


def init():
    Base.metadata.bind = DB_ENGINE
    Base.metadata.create_all(bind=DB_ENGINE)

    with db_context() as session:
        user = SuperUser().as_usercreate()
        if UserQuery(session).create_user(user):
            print(f"Admin {user.username} is created!", file=sys.stderr)
        else:
            print(f"Admin {user.username} already exists!", file=sys.stderr)


def deinit():
    Base.metadata.bind = DB_ENGINE
    Base.metadata.drop_all(bind=DB_ENGINE)
    print("deinit is done!", file=sys.stderr)


def sync_usage():
    with redis_context() as redis:
        with db_context() as session:
            copy_yesterday_usage(redis, session)
