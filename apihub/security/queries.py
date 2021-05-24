from typing import List

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import Query

from ..common.queries import BaseQuery
from .models import User
from .schemas import UserSession, UserCreate
from .helpers import hash_password


class UserException(Exception):
    pass


class UserQuery(BaseQuery):
    def get_query(self) -> Query:
        return self.session.query(User)

    def get_user_by_id(self, user_id: int) -> UserSession:
        user = self.get_query().filter(User.id == user_id).one()
        return UserSession(
            id=user.id,
            username=user.username,
            role=user.role,
            salt=user.salt,
            hashed_password=user.hashed_password,
        )

    def get_user_by_username_and_password(
        self, username: str, password: str
    ) -> UserSession:
        try:
            user = self.get_query().filter(User.username == username).one()
        except NoResultFound:
            raise UserException

        _, hashed_password = hash_password(password, salt=user.salt)
        if user.hashed_password == hashed_password:
            return UserSession(
                id=user.id,
                username=user.username,
                role=user.role,
                salt=user.salt,
                hashed_password=user.hashed_password,
            )
        raise UserException

    def get_user_by_username(self, username: str) -> UserSession:
        try:
            user = self.get_query().filter(User.username == username).one()
        except NoResultFound:
            raise UserException

        return UserSession(
            id=user.id,
            username=user.username,
            role=user.role,
            salt=user.salt,
            hashed_password=user.hashed_password,
        )

    def get_users_by_usernames(self, usernames: List[str]) -> List[UserSession]:
        try:
            users = self.get_query().filter(User.username.in_(usernames))
        except NoResultFound:
            raise UserException

        return [
            UserSession(
                id=user.id,
                username=user.username,
                role=user.role,
                salt=user.salt,
                hashed_password=user.hashed_password,
            )
            for user in users
        ]

    def create_user(self, user: UserCreate) -> bool:
        """ """
        db_user = User(**user.make_user().dict())
        self.session.add(db_user)
        self.session.commit()
        # FIXME
        return True

    def change_password(self, username: str, password: str) -> bool:
        """ """
        try:
            user_in_db = self.get_query().filter(User.username == username).one()
        except NoResultFound:
            raise UserException

        _, hashed_password = hash_password(password, salt=user_in_db.salt)
        user_in_db.hashed_password = hashed_password

        return True
