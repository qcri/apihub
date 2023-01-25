import sys

from pydantic import BaseSettings

from apihub.common.db_session import db_context, Base, DB_ENGINE, create_session
from apihub.common.redis_session import redis_conn
from apihub.security.schemas import UserCreate, UserType, ProfileBase
from apihub.security.queries import UserQuery
from apihub.security.models import *
from apihub.subscription.queries import SubscriptionQuery
from apihub.subscription.models import *
from apihub.subscription.schemas import ( ApplicationCreate, SubscriptionCreate, )
from apihub.activity.models import *


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
    print("\n".join(Base.metadata.tables.keys()), file=sys.stderr)

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
    data = yaml.safe_load(open(filename, 'r', encoding='utf-8'),)
    with db_context() as session:
        users = {}
        applications = {}
        pricings = {}
        subscriptions = {}
        for name, items in data.items():
            if name == 'user':
                for item in items:
                    profile_data = ProfileBase(**item)
                    name = profile_data.first_name + " " + profile_data.last_name
                    user_data = UserCreate(name=name, **item)
                    user = User(**user_data.make_user().dict())
                    session.add(user)

                    profile = Profile(
                        user_id=user.id,
                        **profile_data.dict(),
                    )
                    session.add(profile)
                    users[user.email] = user
            elif name == 'application':
                for item in items:
                    application_data = ApplicationCreate(**item)
                    pricings = []
                    for pricing in item['pricings']:
                        pricing = Pricing(
                            tier=pricing['tier'],
                            credit=pricing['credit'],
                            price=pricing['price'],
                        )
                        pricings.append(pricing)
                    application = Application(
                        name=application_data.name,
                        url=application_data.url,
                        description=application_data.description,
                        user_id=users[item['user']].id,
                        pricings=pricings,
                    )
                    session.add(application)
                    applications[application.name] = application
            # elif name == 'subscription':
            #     for item in items:
            #         subscription = Subscription(
            #             user_id=users[item.user].id,
            #             application_id=applications[item.application].id,
            #             pricing_id=pricings[item.pricing].id,
            #             expires_at=item.expires_at,
            #         )
            #         subscriptions[subscription.user_id] = subscription
            else:
                print(f"model {name} not supported", file=sys.stderr)
