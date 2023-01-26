from typing import List
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import true
from redis import Redis
from sqlalchemy.orm import Query

from ..common.queries import BaseQuery
from .models import Subscription, Application, Pricing
from .schemas import (
    SubscriptionCreate,
    SubscriptionDetails,
    ApplicationCreate,
    ApplicationCreateWithOwner,
    PricingBase,
)
from .helpers import get_and_reset_balance_in_cache


class ApplicationException(Exception):
    pass


class PricingException(Exception):
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

    def create_application(self, application: ApplicationCreateWithOwner) -> ApplicationCreateWithOwner:
        """
        Create an application.
        :param application: Application details.
        :return: Application object.
        """
        pricings = []
        for pricing in application.pricings:
            pricings.append(
                Pricing(
                    tier=pricing.tier,
                    price=pricing.price,
                    credit=pricing.credit,
                )
            )
        application_object = Application(
            name=application.name,
            url=application.url,
            description=application.description,
            pricings=pricings,
        )
        try:
            self.session.add(application_object)
            self.session.commit()
            return application
        except Exception as e:
            self.session.rollback()
            raise ApplicationException(f"Error creating application: {e}")

    def get_application(self, application_id: int) -> ApplicationCreate:
        """
        Get application by name.
        :param name: Application name.
        :return: application object.
        """
        try:
            application = self.get_query().filter(Application.id == application_id).one()
            return application.to_schema(with_pricing=True)
        except NoResultFound:
            raise ApplicationException(f"Application {application_id} not found.")

    def get_application_by_path(self, path: str) -> ApplicationCreate:
        """
        Get application by name.
        :param name: Application name.
        :return: application object.
        """
        try:
            application = self.get_query().filter(Application.path == path).one()
            return application.to_schema(with_pricing=True)
        except NoResultFound:
            raise ApplicationException(f"Application with path {path} not found.")

    def get_applications(self, email=None) -> List[ApplicationCreate]:
        """
        List applications.
        :return: List of applications.
        """
        applications = map(lambda x: x.to_schema(), self.get_query().all())
        return list(applications)


class PricingQuery(BaseQuery):
    def get_query(self) -> Query:
        """
        Get query object.
        :return: Query object.
        """
        return self.session.query(Pricing)

    def create_subscription_pricing(
        self, tier: str, application: str, price: int, credit: int
    ) -> Pricing:
        """
        Create subscription pricing.
        :param tier: Subscription tier.
        :param application: Application name.
        :param price: Price.
        :param credit: Credit.
        :return: Pricing object.
        """
        subscription_pricing = Pricing(
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
            raise PricingException(
                f"Error creating subscription pricing: {e}"
            )

    def get_subscription_pricing(
        self, application_id: int, tier: str
    ) -> Pricing:
        """
        Get subscription pricing by application name and tier.
        :param application: Application name.
        :param tier: Subscription tier.
        :return: Pricing object.
        """
        try:
            return (
                self.get_query()
                .filter(
                    Pricing.application_id == application_id,
                    Pricing.tier == tier,
                )
                .one()
            )
        except NoResultFound:
            raise PricingException(
                f"Subscription pricing for application {application_id} and tier {tier} not found."
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
                subscription_create.user_id, subscription_create.application_id
            )
        except SubscriptionException:
            found_existing_subscription = False

        if found_existing_subscription:
            raise SubscriptionException(
                "Found existing subscription, please delete it before create new subscription"
            )

        subscription_pricing = PricingQuery(
            self.session
        ).get_subscription_pricing(
            subscription_create.application_id, subscription_create.tier
        )

        new_subscription = Subscription(
            user_id=subscription_create.user_id,
            application_id=subscription_create.application_id,
            pricing_id=subscription_create.pricing_id,
            tier=subscription_create.tier,
            credit=subscription_pricing.credit,
            balance=subscription_pricing.credit,
            expires_at=subscription_create.expires_at,
            recurring=subscription_create.recurring,
        )
        try:
            self.session.add(new_subscription)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise SubscriptionException(f"Error creating subscription: {e}")

    def get_active_subscription_by_path(
        self, user_id: int, path: str
    ) -> SubscriptionDetails:
        """
        Get active subscription of a user.
        :param email: str
        :param application: str
        :return: SubscriptionDetails object.
        """
        try:
            application = self.session.query(Application).filter(
                Application.path == path
            ).one()

            subscription = self.get_query().filter(
                    Subscription.user_id == user_id,
                    Subscription.application_id == application.id,
                    Subscription.is_active == true(),
                    or_(
                        Subscription.expires_at.is_(None),
                        Subscription.expires_at > datetime.now(),
                    ),
                ).one()
        except NoResultFound:
            raise SubscriptionException("Subscription not found.")

        return SubscriptionDetails(
            id=subscription.id,
            user_id=subscription.user_id,
            application_id=subscription.application_id,
            pricing_id=subscription.pricing_id,
            tier=subscription.tier,
            is_active=subscription.is_active,
            credit=subscription.credit,
            balance=subscription.balance,
            starts_at=subscription.starts_at,
            expires_at=subscription.expires_at,
            recurring=subscription.recurring,
            created_at=subscription.created_at,
        )

    def get_subscription(self, subscription_id: int) -> SubscriptionDetails:
        try:
            subscription = self.get_query().filter(
                Subscription.id == subscription_id
            ).one()
        except NoResultFound:
            raise SubscriptionException("Subscription not found.")
        
        return SubscriptionDetails(
            id=subscription.id,
            user_id=subscription.user_id,
            application_id=subscription.application_id,
            pricing_id=subscription.pricing_id,
            tier=subscription.tier,
            is_active=subscription.is_active,
            credit=subscription.credit,
            balance=subscription.balance,
            starts_at=subscription.starts_at,
            expires_at=subscription.expires_at,
            recurring=subscription.recurring,
            created_at=subscription.created_at,
        )

    def get_active_subscription(
        self, user_id: int, application_id: int
    ) -> SubscriptionDetails:
        """
        Get active subscription of a user.
        :param email: str
        :param application: str
        :return: SubscriptionDetails object.
        """
        try:
            subscription = (
                self.get_query()
                .filter(
                    Subscription.user_id == user_id,
                    Subscription.application_id == application_id,
                    Subscription.is_active == true(),
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
            id=subscription.id,
            user_id=subscription.user_id,
            application_id=subscription.application_id,
            pricing_id=subscription.pricing_id,
            tier=subscription.tier,
            is_active=subscription.is_active,
            credit=subscription.credit,
            balance=subscription.balance,
            starts_at=subscription.starts_at,
            expires_at=subscription.expires_at,
            recurring=subscription.recurring,
            created_at=subscription.created_at,
        )

    def get_active_subscriptions(self, user_id: int) -> List[SubscriptionDetails]:
        """
        Get all active subscriptions of a user.
        :param email: str
        :return: list of SubscriptionDetails.
        """
        try:
            subscriptions = self.get_query().filter(
                Subscription.user_id == user_id,
                Subscription.is_active == true(),
                or_(
                    Subscription.expires_at.is_(None),
                    Subscription.expires_at > datetime.now(),
                ),
            )
        except NoResultFound:
            raise SubscriptionException

        return [
            SubscriptionDetails(
                id=subscription.id,
                user_id=subscription.user_id,
                application_id=subscription.application_id,
                pricing_id=subscription.pricing_id,
                tier=subscription.tier,
                is_active=subscription.is_active,
                credit=subscription.credit,
                balance=subscription.balance,
                expires_at=subscription.expires_at,
                recurring=subscription.recurring,
                created_at=subscription.created_at,
            )
            for subscription in subscriptions
        ]

    def update_balance_in_subscription(
        self, subscription: Subscription, redis: Redis
    ) -> None:
        """
        Update balance in subscription.
        :param email: str
        :param application: str
        :param tier: str
        :param redis: Redis object.
        :return: None
        """
        with get_and_reset_balance_in_cache(
            # FIXME why not use subscription.id?
            subscription.user_id, subscription.application_id, subscription.tier, redis
        ) as balance:
            subscription.balance = subscription.credit - balance
            self.session.add(subscription)
            self.session.commit()
