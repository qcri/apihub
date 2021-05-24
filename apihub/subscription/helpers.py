from redis import Redis


# increment usage on redis
def make_key(username: str, application: str) -> str:
    return f"usage:{username}:{application}"


def record_usage(username: str, application: str, redis: Redis) -> None:
    redis.incr(make_key(username, application))
