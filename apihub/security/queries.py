from typing import List, Optional

from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm.exc import NoResultFound

from ..common.queries import BaseQuery
from .models import User
from .schemas import UserBase, UserSession, UserCreate
from .helpers import hash_password
from sqlalchemy.orm import Query


class UserException(Exception):
    pass


class UserQuery(BaseQuery):
    def get_query(self) -> Query:
        """
        Get query.
        :return: Query object.
        """
        return self.session.query(User)

    def get_user_by_id(self, user_id: int) -> UserSession:
        """
        Get user by id
        :param user_id: integer id
        :return: UserSession object.
        """
        try:
            user = self.get_query().filter(User.id == user_id).one()
            return UserSession(
                id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
                salt=user.salt,
                hashed_password=user.hashed_password,
            )
        except NoResultFound:
            raise UserException("User not found.")

    def get_user_by_email_and_password(
        self, email: str, password: str
    ) -> UserSession:
        """
        Get user by email and password.
        :param email: str
        :param password: str
        :return: UserSession object.
        """
        try:
            user = self.get_query().filter(User.email == email).one()
        except NoResultFound:
            raise UserException

        _, hashed_password = hash_password(password, salt=user.salt)
        if user.hashed_password == hashed_password:
            return UserSession(
                id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
                salt=user.salt,
                hashed_password=user.hashed_password,
            )
        raise UserException

    def get_user_by_email(self, email: str) -> UserSession:
        """
        Get user by email.
        :param email: str
        :return: UserSession object.
        """
        try:
            user = self.get_query().filter(User.email == email).one()
        except NoResultFound:
            raise UserException

        return UserSession(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            salt=user.salt,
            hashed_password=user.hashed_password,
        )

    def get_users_by_emails(self, emails: List[str]) -> List[UserSession]:
        """
        Get users by emails.
        :param emails: str
        :return: list of UserSession object.
        """
        try:
            users = self.get_query().filter(User.email.in_(emails))
        except NoResultFound:
            raise UserException

        return [
            UserSession(
                id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
                salt=user.salt,
                hashed_password=user.hashed_password,
            )
            for user in users
        ]

    def get_users_by_role(self, role) -> List[UserBase]:
        """
        Get users by role.
        :param role: str
        :return: list of UserBase objects.
        """
        try:
            users = self.get_query().filter(User.role == role)
        except (DataError, NoResultFound):
            return []

        return [
            UserBase(
                name=user.name,
                email=user.email,
                role=user.role,
            )
            for user in users
        ]

    def create_user(self, user: UserCreate) -> Optional[int]:
        """
        Create a new user.
        :param user: UserCreate object.
        :return: boolean.
        """
        db_user = User(**user.make_user().dict())
        self.session.add(db_user)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            return False

        return db_user.id

    def change_password(self, email: str, password: str) -> bool:
        """
        Change password for a user.
        :param email: str
        :param password: str
        :return: boolean.
        """
        try:
            user_in_db = self.get_query().filter(User.email == email).one()
        except NoResultFound:
            raise UserException(f"User {email} not found")

        _, hashed_password = hash_password(password, salt=user_in_db.salt)
        user_in_db.hashed_password = hashed_password

        return True
