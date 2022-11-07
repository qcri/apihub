from typing import List
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import true
from redis import Redis
from sqlalchemy.orm import Query

from ..common.queries import BaseQuery
from .models import Subscription
from .schemas import SubscriptionCreate, SubscriptionDetails
from .helpers import get_and_reset_balance_in_cache


class SubscriptionException(Exception):
    pass


class SubscriptionQuery(BaseQuery):
    def get_query(self) -> Query:
        """
        Get query object.
        :return: Query object.
        """
        return self.session.query(Subscription)

    def create_subscription(self, subscription_create: SubscriptionCreate):
        """
        Create a new subscription.
        :param subscription_create:
        :return: None
        """
        # check existing subscription
        found_existing_subscription = True
        try:
            self.get_active_subscription(
                subscription_create.username, subscription_create.application
            )
        except SubscriptionException:
            found_existing_subscription = False

        if found_existing_subscription:
            raise SubscriptionException(
                "Found existing subscription, please delete it before create new subscription"
            )

        new_subscription = Subscription(
            username=subscription_create.username,
            application=subscription_create.application,
            active=subscription_create.active,
            tier=subscription_create.tier,
            credit=subscription_create.credit,
            expires_at=subscription_create.expires_at,
            recurring=subscription_create.recurring,
            created_by=subscription_create.created_by,
        )
        self.session.add(new_subscription)
        self.session.commit()

    def get_active_subscription(
        self, username: str, application: str
    ) -> SubscriptionDetails:
        """
        Get active subscription of a user.
        :param username: str
        :param application: str
        :return: SubscriptionDetails object.
        """
        try:
            subscription = (
                self.get_query()
                .filter(
                    Subscription.username == username,
                    Subscription.application == application,
                    Subscription.active == true(),
                    or_(
                        Subscription.expires_at.is_(None),
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
            tier=subscription.tier,
            active=subscription.active,
            credit=subscription.credit,
            balance=subscription.balance,
            starts_at=subscription.starts_at,
            expires_at=subscription.expires_at,
            recurring=subscription.recurring,
            created_by=subscription.created_by,
            created_at=subscription.created_at,
        )

    def get_active_subscriptions(self, username: str) -> List[SubscriptionDetails]:
        """
        Get all active subscriptions of a user.
        :param username: str
        :return: list of SubscriptionDetails.
        """
        try:
            subscriptions = self.get_query().filter(
                Subscription.username == username,
                Subscription.active == true(),
                or_(
                    Subscription.expires_at.is_(None),
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
                    tier=subscription.tier,
                    active=subscription.active,
                    credit=subscription.credit,
                    balance=subscription.balance,
                    expires_at=subscription.expires_at,
                    recurring=subscription.recurring,
                )
            )
        return data

    def update_balance_in_subscription(
        self, username: str, application: str, tier: str, redis: Redis
    ) -> None:
        """
        Update balance in subscription.
        :param username: str
        :param application: str
        :param tier: str
        :param redis: Redis object.
        :return: None
        """
        try:
            subscription = (
                self.get_query()
                .filter(
                    Subscription.username == username,
                    Subscription.application == application,
                    Subscription.tier == tier,
                    Subscription.active == true(),
                    or_(
                        Subscription.expires_at.is_(None),
                        Subscription.expires_at > datetime.now(),
                    ),
                )
                .one()
            )
        except NoResultFound:
            raise SubscriptionException

        with get_and_reset_balance_in_cache(
            username, application, tier, redis
        ) as balance:
            subscription.balance = subscription.credit - balance
            self.session.add(subscription)
            self.session.commit()
