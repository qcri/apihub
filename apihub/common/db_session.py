from contextlib import contextmanager
from typing import Iterator, ContextManager, Callable

import sqlalchemy
from pydantic import BaseSettings
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base


class Settings(BaseSettings):
    db_uri: str


Base: DeclarativeMeta = declarative_base()


DB_ENGINE = sqlalchemy.engine_from_config(
    {
        "url": Settings().db_uri,
        "echo": False,
    },
    prefix="",
)


def create_session() -> Iterator[Session]:
    session = sessionmaker(bind=DB_ENGINE)()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


db_context: Callable[[], ContextManager[Session]] = contextmanager(create_session)
