from typing import List
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import true
from redis import Redis
from sqlalchemy.orm import Query

from ..common.queries import BaseQuery
from .models import Subscription, Application, SubscriptionPricing
from .schemas import (
    SubscriptionCreate,
    SubscriptionDetails,
    ApplicationCreate,
    SubscriptionPricingCreate2,
)
from .helpers import get_and_reset_balance_in_cache


class ApplicationException(Exception):
    pass


class SubscriptionPricingException(Exception):
    pass


class SubscriptionException(Exception):
    pass


class ApplicationQuery(BaseQuery):
    def get_query(self) -> Query:
        """
        Get query object.
        :return: Query object.
        """
        return self.session.query(Application)

    def create_application(self, application: ApplicationCreate):
        """
        Create an application.
        :param application: Application details.
        :return: Application object.
        """
        pricing_list = []
        for pricing in application.pricing:
            pricing_list.append(
                SubscriptionPricing(
                    tier=pricing.tier,
                    price=pricing.price,
                    credit=pricing.credit,
                    application=application.name,
                )
            )
        application_object = Application(
            name=application.name,
            url=application.url,
            description=application.description,
            subscriptions_pricing=pricing_list,
        )
        try:
            self.session.add(application_object)
            self.session.commit()
            return application
        except Exception as e:
            self.session.rollback()
            raise ApplicationException(f"Error creating application: {e}")

    def get_application(self, name: str) -> ApplicationCreate:
        """
        Get application by name.
        :param name: Application name.
        :return: List of application pricing.
        """
        try:
            application = self.get_query().filter(Application.name == name).one()
            application_create = ApplicationCreate(
                name=application.name,
                url=application.url,
                description=application.description,
                pricing=[],
            )
            for pricing in application.subscriptions_pricing:
                application_create.pricing.append(
                    SubscriptionPricingCreate2(
                        tier=pricing.tier,
                        price=pricing.price,
                        credit=pricing.credit,
                    )
                )
            return application_create
        except NoResultFound:
            raise ApplicationException(f"Application {name} not found.")

    def list_applications(self) -> List[ApplicationCreate]:
        """
        List applications.
        :return: List of applications.
        """
        application_list = []
        for application in self.get_query().all():
            application_list.append(self.get_application(application.name))
        return application_list


class SubscriptionPricingQuery(BaseQuery):
    def get_query(self) -> Query:
        """
        Get query object.
        :return: Query object.
        """
        return self.session.query(SubscriptionPricing)

    def create_subscription_pricing(
        self, tier: str, application: str, price: int, credit: int
    ) -> SubscriptionPricing:
        """
        Create subscription pricing.
        :param tier: Subscription tier.
        :param application: Application name.
        :param price: Price.
        :param credit: Credit.
        :return: SubscriptionPricing object.
        """
        subscription_pricing = SubscriptionPricing(
            tier=tier,
            application=application,
            price=price,
            credit=credit,
        )
        try:
            self.session.add(subscription_pricing)
            self.session.commit()
            return subscription_pricing
        except Exception as e:
            self.session.rollback()
            raise SubscriptionPricingException(
                f"Error creating subscription pricing: {e}"
            )

    def get_subscription_pricing(
        self, application: str, tier: str
    ) -> SubscriptionPricing:
        """
        Get subscription pricing by application name and tier.
        :param application: Application name.
        :param tier: Subscription tier.
        :return: SubscriptionPricing object.
        """
        try:
            return (
                self.get_query()
                .filter(
                    SubscriptionPricing.application == application,
                    SubscriptionPricing.tier == tier,
                )
                .one()
            )
        except NoResultFound:
            raise SubscriptionPricingException(
                f"Subscription pricing for application {application} and tier {tier} not found."
            )


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

        subscription_pricing = SubscriptionPricingQuery(
            self.session
        ).get_subscription_pricing(
            subscription_create.application, subscription_create.tier
        )

        new_subscription = Subscription(
            username=subscription_create.username,
            application=subscription_create.application,
            active=subscription_create.active,
            tier=subscription_create.tier,
            credit=subscription_pricing.credit,
            balance=subscription_pricing.credit,
            expires_at=subscription_create.expires_at,
            recurring=subscription_create.recurring,
            created_by=subscription_create.created_by,
        )
        try:
            self.session.add(new_subscription)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise SubscriptionException(f"Error creating subscription: {e}")

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
