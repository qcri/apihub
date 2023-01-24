import sys

from pydantic import BaseSettings

from apihub.common.db_session import db_context, Base, DB_ENGINE
from apihub.common.redis_session import redis_conn
from apihub.security.schemas import UserCreate, UserType
from apihub.security.queries import UserQuery
from apihub.security.models import User, Profile
from apihub.subscription.queries import SubscriptionQuery
from apihub.subscription.models import Application, Subscription, Pricing


class SuperUser(BaseSettings):
    name: str
    password: str
    email: str

    def as_usercreate(self):
        return UserCreate(
            name=self.name,
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
        print(f"Admin {user.name} is created!", file=sys.stderr)


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
    print("deinit is done!", file=sys.stderr)


def load_data(filename):
    import yaml
    data = yaml.load(open(filename, 'r', encoding='utf-8'),)
    for name, items in data.items():
        if name == 'user':
            with db_context() as session:
                query = UserQuery(session)
                for item in items:
                    user_id = query.create_user(
                        UserCreate(
                            name=item.name,
                            email=item.email,
                            password=item.password,
                            role=item.role,
                        )
                    )
                    if user_id:
        elif name == 'application':
            for item in items:
        else:
            print(f"model {name} not supported", file=sys.stderr)
