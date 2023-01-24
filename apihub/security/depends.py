from typing import Optional, List
from pydantic import BaseModel

from fastapi import HTTPException, Depends, Request
from fastapi_jwt_auth import AuthJWT

from .schemas import UserBaseWithId


HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_403_FORBIDDEN = 403


class RateLimits(BaseModel):
    limit: int
    window_secs: int


def rate_limited(key: str, limits: RateLimits, redis):
    p = redis.pipeline()
    p.incr(key)
    p.ttl(key)
    num, expire = p.execute()
    if num == 1 or expire == -1:
        redis.expire(key, limits.window_secs)
    if num > limits.limit:
        raise HTTPException(
            HTTP_429_TOO_MANY_REQUESTS,
            "Too Many Requests",
            headers={"Retry-After": str(expire)},
        )


class RateLimiter:
    def __init__(self, key: str, limits: RateLimits, redis):
        self.key = key
        self.limits = limits
        self.redis = redis

    def __call__(self, request: Request):
        if self.key == "ip":
            key = request.client.host
        else:
            key = self.key
        rate_limited(key, self.limits, self.redis)


class UserOfRole:
    def __init__(self, role: Optional[str] = None, roles: List[str] = list()):
        self.roles = [role] if role is not None else roles

    def __call__(self, Authorize: AuthJWT = Depends()):
        Authorize.jwt_required()

        claims = Authorize.get_raw_jwt()
        role = claims.get("role", "")
        if role in self.roles:
            name = claims.get("name", "")
            email = Authorize.get_jwt_subject()
            user_id = claims.get("id", "")
            return UserBaseWithId(
                id=user_id,
                name=name,
                email=email,
                role=role,
            )

        raise HTTPException(
            HTTP_403_FORBIDDEN,
            "The API key doesn't have permission to perform the request",
        )


def require_token(Authorize: AuthJWT = Depends()) -> UserBaseWithId:
    Authorize.jwt_required()
    claims  = Authorize.get_raw_jwt()
    role = claims.get("role", "")
    name = claims.get("name", "")
    email = Authorize.get_jwt_subject()
    user_id = claims.get("id", "")
    return UserBaseWithId(
        id=user_id,
        name=name,
        email=email,
        role=role,
    )


require_admin = UserOfRole(role="admin")
require_publisher = UserOfRole(role="publisher")
require_user = UserOfRole(role="user")
require_app = UserOfRole(role="app")
require_publisher_or_admin = UserOfRole(roles=["admin", "publisher"])
require_logged_in = UserOfRole(roles=["admin", "publisher", "user", "app"])
