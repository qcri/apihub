from typing import List
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound

from ..common.queries import BaseQuery
from .models import Subscription, Usage
from .schemas import SubscriptionCreate, SubscriptionDetails, UsageDetails


class UsageException(Exception):
    pass


class SubscriptionException(Exception):
    pass


class ApplicationQuery(BaseQuery):
    def create_subscription(self, subscription_create: SubscriptionCreate):
        new_subscription = Subscription(
            username=subscription_create.username,
            application=subscription_create.application,
            limit=subscription_create.limit,
            expires_at=subscription_create.expires_at,
            recurring=subscription_create.recurring,
            created_by=subscription_create.created_by,
        )
        self.session.add(new_subscription)
        self.session.commit()

    def get_active_subscription(
        self, username: str, application: str
    ) -> SubscriptionDetails:
        try:
            subscription = (
                self.session.query(Subscription)
                .filter(
                    Subscription.username == username,
                    Subscription.application == application,
                    or_(
                        Subscription.expires_at == None,  # noqa
                        Subscription.expires_at > datetime.now(),
                    ),
                )
                .one()
            )
        except NoResultFound:
            raise SubscriptionException

        return SubscriptionDetails(
            username=username,
            application=application,
            limit=subscription.limit,
            starts_at=subscription.starts_at,
            expires_at=subscription.expires_at,
            recurring=subscription.recurring,
            created_by=subscription.created_by,
            created_at=subscription.created_at,
        )

    def get_active_subscriptions(self, username: str) -> List[SubscriptionDetails]:
        try:
            subscriptions = self.session.query(Subscription).filter(
                Subscription.username == username,
                or_(
                    Subscription.expires_at is None,
                    Subscription.expires_at > datetime.now(),
                ),
            )
        except NoResultFound:
            raise SubscriptionException

        data = []
        for subscription in subscriptions:
            data.append(
                SubscriptionDetails(
                    username=subscription.username,
                    application=subscription.application,
                    limit=subscription.limit,
                    expires_at=subscription.expires_at,
                    recurring=subscription.recurring,
                )
            )
        return data

    def create_usage_from_subscription(self, subscription: SubscriptionCreate) -> Usage:
        # TODO get_or_create_usage
        # TODO try except rollback??
        new_usage = Usage(
            username=subscription.username,
            application=subscription.application,
            usage=0,
            expires_at=subscription.expires_at,
        )
        self.session.add(new_usage)
        self.session.commit()
        return new_usage

    def get_active_usage(self, username: str, application: str) -> UsageDetails:
        # TODO get all results and verify if there is only one result
        try:
            usage = (
                self.session.query(Usage)
                .filter(
                    Usage.username == username,
                    Usage.application == application,
                    or_(
                        Usage.expires_at == None,  # noqa
                        Usage.expires_at > datetime.now(),
                    ),
                )
                .one()
            )
        except NoResultFound:
            raise UsageException

        return UsageDetails(
            username=usage.username,
            application=usage.application,
            usage=usage.usage,
            starts_at=usage.starts_at,
            expires_at=usage.expires_at,
        )

    def get_active_usages(self, username: str) -> List[UsageDetails]:
        try:
            usages = self.session.query(Usage).filter(
                Usage.username == username,
                or_(
                    Usage.expires_at == None,  # noqa
                    Usage.expires_at > datetime.now(),
                ),
            )
        except NoResultFound:
            raise UsageException

        data = []
        for usage in usages:
            data.append(
                UsageDetails(
                    username=usage.username,
                    application=usage.application,
                    usage=usage.usage,
                    starts_at=usage.starts_at,
                    expires_at=usage.expires_at,
                )
            )
        return data

    def get_history_usages(self, username: str, application: str) -> List[UsageDetails]:
        usages = self.session.query(Usage).filter(
            Usage.username == username,
            Usage.application == application,
        )
        data = []
        for usage in usages:
            data.append(
                UsageDetails(
                    username=usage.username,
                    application=usage.application,
                    usage=usage.usage,
                    starts_at=usage.starts_at,
                    expires_at=usage.expires_at,
                )
            )
        return data
