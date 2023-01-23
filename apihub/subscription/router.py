from datetime import datetime, timedelta
from typing import Optional, List

from pydantic import BaseModel, BaseSettings
from fastapi import APIRouter, Depends, HTTPException
from fastapi_jwt_auth import AuthJWT

from ..common.db_session import create_session
from ..security.schemas import (
    UserBase,
)
from ..security.depends import require_admin, require_publisher, require_token
from ..security.queries import UserQuery, UserException

from .schemas import (
    SubscriptionCreate,
    SubscriptionIn,
    ApplicationCreate,
    ApplicationCreateWithOwner,
)
from .queries import (
    SubscriptionQuery,
    SubscriptionException,
    SubscriptionPricingException,
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
        username: str = Depends(require_publisher),
    ):
    """
    Create an application.
    """
    applicationCreateWithOwner = ApplicationCreateWithOwner.copy(
        application,
        update={"owner": username}
    )

    try:
        return ApplicationQuery(session).create_application(applicationCreateWithOwner)
    except ApplicationException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/application", response_model=List[ApplicationCreate])
def get_applications(
        session: Session = Depends(create_session),
        user: UserBase = Depends(require_token),
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
        username: str = Depends(require_admin),
    ):
    try:
        """
        Get an application.
        """
        return ApplicationQuery(session).get_application(application)
    except ApplicationException:
        raise HTTPException(400, "Error while retrieving applications")


@router.post("/subscription")
def create_subscription(
    subscription: SubscriptionIn,
    username: str = Depends(require_admin),
    session=Depends(create_session),
):
    # make sure the username exists.
    try:
        UserQuery(session).get_user_by_username(subscription.username)
    except UserException:
        raise HTTPException(401, f"User {subscription.username} not found.")

    # make sure the application is not currently active.
    try:
        SubscriptionQuery(session).get_active_subscription(
            subscription.username, subscription.application
        )
        raise HTTPException(
            403, f"Application {subscription.application} already exists."
        )
    except SubscriptionException:
        pass

    try:
        ApplicationQuery(session).get_application(subscription.application)
    except ApplicationException:
        raise HTTPException(404, f"Application {subscription.application} not found.")

    if subscription.expires_at is None:
        subscription.expires_at = datetime.now() + timedelta(
            days=SubscriptionSettings().default_subscription_days
        )

    subscription_create = SubscriptionCreate(
        username=subscription.username,
        application=subscription.application,
        tier=subscription.tier,
        starts_at=datetime.now(),
        expires_at=subscription.expires_at,
        recurring=subscription.recurring,
        created_by=username,
    )
    try:
        query = SubscriptionQuery(session)
        query.create_subscription(subscription_create)
        return subscription_create
    except SubscriptionException as e:
        raise HTTPException(400, str(e))
    except SubscriptionPricingException as e:
        raise HTTPException(400, str(e))


@router.get("/subscription/{application}")
def get_active_subscription(
    application: str,
    user: UserBase = Depends(require_token),
    session=Depends(create_session),
):
    query = SubscriptionQuery(session)
    try:
        subscription = query.get_active_subscription(user.username, application)
    except SubscriptionException:
        raise HTTPException(400, "Subscription not found")

    return subscription


@router.get("/subscription")
def get_active_subscriptions(
    user: UserBase = Depends(require_token),
    session=Depends(create_session),
):
    if not user.is_user:
        return []

    username = user.username
    query = SubscriptionQuery(session)
    try:
        subscriptions = query.get_active_subscriptions(username)
    except SubscriptionException:
        return []

    return [
        SubscriptionIn(
            username=subscription.username,
            application=subscription.application,
            tier=subscription.tier,
            expires_at=subscription.expires_at,
            recurring=subscription.recurring,
        )
        for subscription in subscriptions
    ]


class SubscriptionTokenResponse(BaseModel):
    username: str
    application: str
    token: str
    expires_time: int


@router.get("/token/{application}")
async def get_application_token(
    application: str,
    user: UserBase = Depends(require_token),
    username: Optional[str] = None,
    expires_days: Optional[
        int
    ] = SubscriptionSettings().subscription_token_expires_days,
    session=Depends(create_session),
):
    query = SubscriptionQuery(session)

    if user.is_user:
        username = user.username
        expires_days = SubscriptionSettings().subscription_token_expires_days
    else:
        if username is None:
            raise HTTPException(401, "username is missing")

    try:
        subscription = query.get_active_subscription(username, application)
    except SubscriptionException:
        raise HTTPException(401, f"No active subscription found for user {username}")

    if subscription.balance > subscription.credit:
        raise HTTPException(HTTP_429_TOO_MANY_REQUESTS, "You have used up your credit")

    # limit token expire time to subscription expire time
    subscription_expires_timedelta = subscription.expires_at - datetime.now()
    if expires_days > subscription_expires_timedelta.days:
        expires_days = subscription_expires_timedelta.days

    Authorize = AuthJWT()
    expires_time = timedelta(days=expires_days)
    access_token = Authorize.create_access_token(
        subject=username,
        user_claims={"subscription": application, "tier": subscription.tier},
        expires_time=expires_time,
    )
    return SubscriptionTokenResponse(
        username=username,
        application=application,
        token=access_token,
        expires_time=expires_time.seconds,
    )
