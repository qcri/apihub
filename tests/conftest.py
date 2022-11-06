import pytest
from apihub_users.common.db_session import Base, get_db_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy_utils.functions import (
    database_exists,
    create_database,
    drop_database,
)


DB_ENGINE = get_db_engine()


@pytest.fixture(scope="session")
def db_connection():
    if database_exists(DB_ENGINE.url):
        drop_database(DB_ENGINE.url)
    create_database(DB_ENGINE.url)

    Base.metadata.bind = DB_ENGINE
    Base.metadata.create_all()

    # seed database
    yield DB_ENGINE.connect()

    Base.metadata.drop_all()


@pytest.fixture(scope="function")
def db_session(db_connection):
    transaction = db_connection.begin()
    yield scoped_session(
        sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=db_connection,
        )
    )
    transaction.rollback()
