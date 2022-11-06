import datetime

from sqlalchemy.orm import Query
from sqlalchemy.exc import IntegrityError, NoResultFound

from apihub_users.common.queries import BaseQuery

from .models import Activity
from .schemas import ActivityCreate, ActivityDetails


class ActivityException(Exception):
    pass


class ActivityQuery(BaseQuery):
    def get_query(self) -> Query:
        """
        Get query object
        :return: Query object.
        """
        return self.session.query(Activity)

    def create_activity(self, activity_create: ActivityCreate) -> None:
        """
        Create a new activity.
        :param activity_create: ActivityCreate object.
        :return: None
        """
        activity = Activity(**activity_create.dict())
        self.session.add(activity)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise ActivityException("IntegrityError")

    def get_activity_by_key(self, request_key: str) -> ActivityDetails:
        """
        Get activity by request key.
        :param request_key: str
        :return: ActivityDetails object.
        """
        try:
            activity = (
                self.get_query().filter(Activity.request_key == request_key).one()
            )
            return ActivityDetails(
                created_at=activity.created_at,
                request=activity.request,
                tier=activity.tier,
                status=activity.status,
                request_key=activity.request_key,
                result=activity.result,
                payload=activity.payload,
                ip_address=activity.ip_address,
                latency=activity.latency,
            )
        except NoResultFound:
            raise ActivityException

    def update_activity(self, request_key, set_latency=True, **kwargs) -> None:
        """
        Update activity by request key.
        :param request_key: str
        :param set_latency: bool
        :param kwargs: dict of fields to update.
        :return: None
        """
        try:
            activity = (
                self.get_query().filter(Activity.request_key == request_key).one()
            )
            if set_latency:
                kwargs["latency"] = (
                    datetime.datetime.now() - activity.created_at
                ).total_seconds()
        except NoResultFound:
            raise ActivityException

        for key, value in kwargs.items():
            setattr(activity, key, value)

        self.session.add(activity)
        try:
            self.session.commit()
            self.session.refresh(activity)
        except IntegrityError:
            self.session.rollback()
            raise ActivityException("IntegrityError")
