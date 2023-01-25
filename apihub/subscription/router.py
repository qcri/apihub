from datetime import datetime, timedelta
from typing import Optional, List

from pydantic import BaseModel, BaseSettings
from fastapi import APIRouter, Depends, HTTPException
from fastapi_jwt_auth import AuthJWT

from ..common.db_session import create_session
from ..security.schemas import (
    UserBaseWithId,
)
from ..security.depends import require_admin, require_publisher, require_token, require_user, require_logged_in
from ..security.queries import UserQuery, UserException

from .schemas import (
    SubscriptionCreate,
    SubscriptionIn,
    ApplicationCreate,
    ApplicationCreateWithOwner,
    SubscriptionToken,
)
from .queries import (
    SubscriptionQuery,
    SubscriptionException,
    PricingException,
    ApplicationQuery,
    ApplicationException,
)
from sqlalchemy.orm import Session

HTTP_429_TOO_MANY_REQUESTS = 429

router = APIRouter()


class SubscriptionSettings(BaseSettings):
    default_subscription_days: int = 30
    subscription_token_expires_days: int = 1


@router.post("/application", response_model=ApplicationCreate)
def create_application(
        application: ApplicationCreate,
        session: Session = Depends(create_session),
        publisher: str = Depends(require_publisher),
    ):
    """
    Create an application.
    """
    applicationCreateWithOwner = ApplicationCreateWithOwner.copy(
        application,
        update={"owner": publisher}
    )

    try:
        return ApplicationQuery(session).create_application(applicationCreateWithOwner)
    except ApplicationException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/application", response_model=List[ApplicationCreate])
def get_applications(
        session: Session = Depends(create_session),
        user: str = Depends(require_logged_in),
    ):
    """
    List all applications.
    """

    try:
        applications = ApplicationQuery(session).get_applications()
        return applications
    except ApplicationException as e:
        raise HTTPException(400, detail=str(e))


@router.get("/application/{application}", response_model=ApplicationCreate)
def get_application(
        application: str,
        session: Session = Depends(create_session),
        user: str = Depends(require_logged_in),
    ):
    try:
        """
        Get an application.
        """
        return ApplicationQuery(session).get_application_by_name(application)
    except ApplicationException:
        raise HTTPException(400, f"Error while retrieving application {application}")


@router.post("/subscription")
def create_subscription(
    subscription: SubscriptionIn,
    admin: str = Depends(require_admin),
    session=Depends(create_session),
):
    # make sure the email exists.
    try:
        UserQuery(session).get_user_by_id(subscription.user_id)
    except UserException:
        raise HTTPException(401, f"User {subscription.user_id} not found.")

    # make sure the application is not currently active.
    try:
        SubscriptionQuery(session).get_active_subscription(
            subscription.user_id, subscription.application_id
        )
        raise HTTPException(
            403, f"Subscription for applicaiton {subscription.application_id} already exists."
        )
    except SubscriptionException:
        pass

    try:
        ApplicationQuery(session).get_application(subscription.application_id)
    except ApplicationException:
        raise HTTPException(404, f"Application {subscription.application_id} not found.")

    if subscription.expires_at is None:
        subscription.expires_at = datetime.now() + timedelta(
            days=SubscriptionSettings().default_subscription_days
        )

    subscription_create = SubscriptionCreate(
        user_id=subscription.user_id,
        application_id=subscription.application_id,
        pricing_id=subscription.pricing_id,
        tier=subscription.tier,
        starts_at=datetime.now(),
        expires_at=subscription.expires_at,
        recurring=subscription.recurring,
    )
    try:
        query = SubscriptionQuery(session)
        query.create_subscription(subscription_create)
        return subscription_create
    except SubscriptionException as e:
        raise HTTPException(400, str(e))
    except PricingException as e:
        raise HTTPException(400, str(e))


@router.get("/subscription/{application}")
def get_active_subscription(
    application: int,
    user: UserBaseWithId = Depends(require_logged_in),
    session=Depends(create_session),
):
    query = SubscriptionQuery(session)
    try:
        subscription = query.get_active_subscription(user.id, application)
    except SubscriptionException:
        raise HTTPException(400, "Subscription not found")

    return subscription


@router.get("/subscription")
def get_active_subscriptions(
    user: UserBaseWithId = Depends(require_user),
    session=Depends(create_session),
):
    if not user.is_user:
        return []

    query = SubscriptionQuery(session)
    try:
        subscriptions = query.get_active_subscriptions(user.id)
    except SubscriptionException:
        return []

    return subscriptions


class SubscriptionTokenResponse(BaseModel):
    email: str
    application: str
    token: str
    expires_time: int


@router.get("/token/{application}", response_model=SubscriptionToken)
async def get_application_token(
    application: str,
    user: UserBaseWithId = Depends(require_user),
    email: Optional[str] = None,
    expires_days: Optional[
        int
    ] = SubscriptionSettings().subscription_token_expires_days,
    session=Depends(create_session),
):
    query = SubscriptionQuery(session)

    if user.is_user:
        email = user.email
        expires_days = SubscriptionSettings().subscription_token_expires_days
    else:
        if email is None:
            raise HTTPException(401, "email is missing")

    try:
        subscription = query.get_active_subscription_by_name(user.id, application)
    except SubscriptionException:
        raise HTTPException(401, f"No active subscription found for user {email}")

    if subscription.balance > subscription.credit:
        raise HTTPException(HTTP_429_TOO_MANY_REQUESTS, "You have used up your credit")

    # limit token expire time to subscription expire time
    subscription_expires_timedelta = subscription.expires_at - datetime.now()
    if expires_days > subscription_expires_timedelta.days:
        expires_days = subscription_expires_timedelta.days

    subscription_token = SubscriptionToken(
        email=email,
        name = user.name,
        user_id=user.id,
        role=user.role,
        application=application,
        tier=subscription.tier,
        application_id=subscription.application_id,
        subscription_id=subscription.id,
        expires_days=expires_days,
    )
    return subscription_token