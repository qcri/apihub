from abc import ABCMeta

from sqlalchemy.orm import Session


class BaseQuery(metaclass=ABCMeta):
    def __init__(self, session: Session):
        self.session = session
