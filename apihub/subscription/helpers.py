from contextlib import contextmanager

from redis import Redis


BALANCE_KEYS = "balance:keys"


def make_key(subscription) -> str:
    return f"balance:{subscription.user_id}:{subscription.application_id}:{subscription.tier}"


@contextmanager
def get_and_reset_balance_in_cache(
    subscription, redis: Redis
) -> None:
    """
    Get balance from cache and delete it.
    :param email: str
    :param application: str
    :param tier: str
    :param redis: Redis object.
    :return: None
    """
    key = make_key(subscription)
    balance = redis.get(key)

    yield int(balance)

    if int(balance) <= 0:
        redis.srem(BALANCE_KEYS, key)
        redis.delete(key, 0)
