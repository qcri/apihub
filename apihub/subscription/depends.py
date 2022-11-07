from fastapi import HTTPException, Depends
from fastapi_jwt_auth import AuthJWT
from redis import Redis

from apihub.common.db_session import create_session
from apihub.common.redis_session import redis_conn

from .schemas import SubscriptionBase
from .queries import SubscriptionQuery
from .helpers import make_key, BALANCE_KEYS


HTTP_403_FORBIDDEN = 403
HTTP_429_QUOTA = 429


def require_subscription(
    application: str, Authorize: AuthJWT = Depends()
) -> SubscriptionBase:
    """
    This function is used to check if the user has a valid subscription token.
    :param application: str
    :param Authorize: AuthJWT object.
    :return: SubscriptionBase object.
    """
    Authorize.jwt_required()
    username = Authorize.get_jwt_subject()

    claims = Authorize.get_raw_jwt()
    subscription_claim = claims.get("subscription")
    tier_claim = claims.get("tier")
    if subscription_claim != application:
        raise HTTPException(
            HTTP_403_FORBIDDEN,
            "The API key doesn't have permission to perform the request",
        )
    return SubscriptionBase(
        username=username, tier=tier_claim, application=subscription_claim
    )


def require_subscription_balance(
    subscription: SubscriptionBase = Depends(require_subscription),
    redis: Redis = Depends(redis_conn),
    session=Depends(create_session),
) -> str:
    """
    This function is used to check if the user has enough balance to perform.
    :param subscription: str
    :param redis: Redis object.
    :param session: Session object.
    :return: username str.
    """
    username = subscription.username
    tier = subscription.tier
    application = subscription.application

    key = make_key(username, application, tier)
    balance = redis.decr(key)

    if balance == -1:
        subscription = SubscriptionQuery(session).get_active_subscription(
            username, application
        )
        balance = subscription.credit - subscription.balance - 1
        if balance > 0:
            redis.set(key, balance)
            redis.sadd(BALANCE_KEYS, key)

    if balance <= 0:
        SubscriptionQuery(session).update_balance_in_subscription(
            username, application, tier, redis
        )

    if balance < 0:
        raise HTTPException(
            HTTP_429_QUOTA,
            "You have used up all credit for this API",
        )

    return username
