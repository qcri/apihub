import sys

from pydantic import BaseSettings

from apihub.common.db_session import db_context, Base, DB_ENGINE
from apihub.common.redis_session import redis_conn
from apihub.security.schemas import UserCreate, UserType
from apihub.security.queries import UserQuery
from apihub.subscription.queries import SubscriptionQuery


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
    Base.metadata.create_all()

    with db_context() as session:
        user = SuperUser().as_usercreate()
        UserQuery(session).create_user(user)
        sys.stderr.write(f"Admin {user.username} is created!")


def create_all_statements():
    from sqlalchemy import create_mock_engine

    def metadata_dump(sql, *multiparams, **params):
        print(sql.compile(dialect=engine.dialect))

    engine = create_mock_engine("postgresql://", metadata_dump)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine, checkfirst=False)


def deinit():
    Base.metadata.bind = DB_ENGINE
    Base.metadata.drop_all()
    sys.stderr.write("deinit is done!")
