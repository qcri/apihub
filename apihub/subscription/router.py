from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel, BaseSettings
from fastapi import APIRouter, Depends, HTTPException
from fastapi_jwt_auth import AuthJWT

from ..common.db_session import create_session
from ..security.schemas import UserBase  # TODO create a model for this UserBase
from ..security.depends import require_admin, require_user, require_token
from .schemas import SubscriptionCreate
from .queries import ApplicationQuery, SubscriptionException, UsageException

HTTP_429_TOO_MANY_REQUESTS = 429

router = APIRouter()


class SubscriptionSettings(BaseSettings):
    subscription_token_expires_days: int = 1


class SubscriptionIn(BaseModel):
    username: str
    application: str
    limit: int
    expires_at: Optional[datetime] = None
    recurring: bool = False


@router.post("/subscription")
def create_subscription(
    subscription: SubscriptionIn,
    username: str = Depends(require_admin),
    session=Depends(create_session),
):
    subscription_create = SubscriptionCreate(
        username=subscription.username,
        application=subscription.application,
        limit=subscription.limit,
        starts_at=datetime.now(),
        expires_at=subscription.expires_at,
        recurring=subscription.recurring,
        created_by=username,
    )
    query = ApplicationQuery(session)
    query.create_subscription(subscription_create)


@router.get("/subscription/{application}")
def get_active_subscription(
    application: str,
    user: UserBase = Depends(require_token),
    session=Depends(create_session),
):
    query = ApplicationQuery(session)
    try:
        subscription = query.get_active_subscription(user.username, application)
    except SubscriptionException:
        return {}

    return subscription


@router.get("/subscription")
def get_active_subscriptions(
    user: UserBase = Depends(require_token),
    session=Depends(create_session),
):
    if user.is_user:
        username = user.username

    query = ApplicationQuery(session)
    try:
        subscriptions = query.get_active_subscriptions(username)
    except SubscriptionException:
        return []

    return subscriptions


# delete plan
# @router.post("/subscription/_disable")
# def disable_subscription(
#     username: str = Depends(require_admin),
#     session=Depends(create_session),
# )

# disable plan

# enable plan

# get usage summary

# get usages
@router.get("/usage/{application}")
def get_active_usage(
    application: str,
    user: UserBase = Depends(require_token),
    session=Depends(create_session),
):
    query = ApplicationQuery(session)
    try:
        usage = query.get_active_usage(user.username, application)
    except UsageException:
        return {}

    return usage


@router.get("/usage")
async def get_usages(
    user: UserBase = Depends(require_token),
    session=Depends(create_session),
):
    # TODO take username for admin and manager
    query = ApplicationQuery(session)
    try:
        usages = query.get_active_usages(user.username)
    except UsageException:
        return []

    return usages


class SubscriptionTokenResponse(BaseModel):
    username: str
    application: str
    token: str
    expires_time: int


# get application token
@router.get("/token/{application}")
async def get_application_token(
    application: str,
    username: str = Depends(require_user),
    session=Depends(create_session),
):
    query = ApplicationQuery(session)
    try:
        subscription = query.get_active_subscription(username, application)
    except SubscriptionException:
        raise HTTPException(401, "NOt permitted")
    try:
        usage = query.get_active_usage(username, application)
        if usage.usage > subscription.limit:
            raise HTTPException(
                HTTP_429_TOO_MANY_REQUESTS, "You have exceeded your limit"
            )
    except UsageException:
        query.create_usage_from_subscription(subscription)

    Authorize = AuthJWT()
    expires_days = SubscriptionSettings().subscription_token_expires_days
    expires_time = timedelta(days=expires_days)
    access_token = Authorize.create_access_token(
        subject=username,
        user_claims={"subscription": application},
        expires_time=expires_time,
    )
    return SubscriptionTokenResponse(
        username=username,
        application=application,
        token=access_token,
        expires_time=expires_time.seconds,
    )
