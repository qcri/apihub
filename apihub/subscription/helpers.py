from contextlib import contextmanager

from redis import Redis


BALANCE_KEYS = "balance:keys"


def make_key(username: str, application: str, tier: str) -> str:
    """
    Make key for redis.
    :param username: str
    :param application: str
    :param tier: str
    :return: str.
    """
    return f"balance:{username}:{application}:{tier}"


@contextmanager
def get_and_reset_balance_in_cache(
    username: str, application: str, tier: str, redis: Redis
) -> None:
    """
    Get balance from cache and delete it.
    :param username: str
    :param application: str
    :param tier: str
    :param redis: Redis object.
    :return: None
    """
    key = make_key(username, application, tier)
    balance = redis.get(key)

    yield int(balance)

    if int(balance) <= 0:
        redis.srem(BALANCE_KEYS, key)
        redis.delete(key, 0)
