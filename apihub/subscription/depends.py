from pydantic import BaseModel
from fastapi import HTTPException, Depends
from fastapi_jwt_auth import AuthJWT
from redis import Redis

from ..common.db_session import create_session
from ..common.redis_session import redis_conn

from .schemas import SubscriptionToken
from .queries import SubscriptionQuery
from .helpers import make_key, BALANCE_KEYS


HTTP_403_FORBIDDEN = 403
HTTP_429_QUOTA = 429


def require_subscription(
    application: str, Authorize: AuthJWT = Depends()
) -> SubscriptionToken:
    """
    This function is used to check if the user has a valid subscription token.
    :param application: str
    :param Authorize: AuthJWT object.
    :return: SubscriptionBase object.
    """
    Authorize.jwt_required()
    subscription_token = SubscriptionToken.from_token(Authorize)

    if  subscription_token.application != application:
        raise HTTPException(
            HTTP_403_FORBIDDEN,
            "The API key doesn't have permission to perform the request",
        )

    return subscription_token


def require_subscription_balance(
    subscription: SubscriptionToken = Depends(require_subscription),
    redis: Redis = Depends(redis_conn),
    session=Depends(create_session),
) -> SubscriptionToken:
    """
    This function is used to check if the user has enough balance to perform.
    :param subscription: str
    :param redis: Redis object.
    :param session: Session object.
    :return: email str.
    """
    key = make_key(subscription)
    balance = redis.decr(key)
    

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