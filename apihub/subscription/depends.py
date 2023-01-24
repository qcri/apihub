from pydantic import BaseModel
from fastapi import HTTPException, Depends
from fastapi_jwt_auth import AuthJWT
from redis import Redis

from ..common.db_session import create_session
from ..common.redis_session import redis_conn

from .queries import SubscriptionQuery
from .helpers import make_key, BALANCE_KEYS


HTTP_403_FORBIDDEN = 403
HTTP_429_QUOTA = 429


class SubscriptionResponse(BaseModel):
    user_id: int
    subscription_id: int
    application_id: int
    email: str
    tier: str
    application: str


def require_subscription(
    application: str, Authorize: AuthJWT = Depends()
) -> SubscriptionResponse:
    """
    This function is used to check if the user has a valid subscription token.
    :param application: str
    :param Authorize: AuthJWT object.
    :return: SubscriptionBase object.
    """
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    claims = Authorize.get_raw_jwt()
    subscription = claims.get("subscription")
    tier = claims.get("tier")
    if  subscription != application:
        raise HTTPException(
            HTTP_403_FORBIDDEN,
            "The API key doesn't have permission to perform the request",
        )
    user_id = claims.get("use_id", -1)
    subscription_id = claims.get("subscription_id", -1)
    application_id = claims.get("application_id", -1)
    return SubscriptionResponse(
        user_id=user_id, subscription_id=subscription_id,
        email=email, tier=tier, application=subscription,
        application_id=application_id,
    )


def require_subscription_balance(
    subscription: SubscriptionResponse = Depends(require_subscription),
    redis: Redis = Depends(redis_conn),
    session=Depends(create_session),
) -> SubscriptionResponse:
    """
    This function is used to check if the user has enough balance to perform.
    :param subscription: str
    :param redis: Redis object.
    :param session: Session object.
    :return: email str.
    """
    key = make_key(subscription)
    balance = redis.decr(key)
    

    print("balance", balance)

    if balance is None or balance == -1:
        subscription = SubscriptionQuery(session).get_subscription(
            subscription.subscription_id
        )
        balance = subscription.credit - subscription.balance - 1
        if balance > 0:
            redis.set(key, balance)
            redis.sadd(BALANCE_KEYS, key)

    if balance <= 0:
        SubscriptionQuery(session).update_balance_in_subscription(
            subscription, redis
        )

    if balance < 0:
        raise HTTPException(
            HTTP_429_QUOTA,
            "You have used up all credit for this API",
        )

    return subscription