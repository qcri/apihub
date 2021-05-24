from fastapi import HTTPException, Depends
from fastapi_jwt_auth import AuthJWT


HTTP_403_FORBIDDEN = 403


def require_subscription(application: str, Authorize: AuthJWT = Depends()) -> str:
    Authorize.jwt_required()

    claims = Authorize.get_raw_jwt()
    subscription_claim = claims.get("subscription")
    if subscription_claim != application:
        raise HTTPException(
            HTTP_403_FORBIDDEN,
            "The API key doesn't have permission to perform the request",
        )
    return Authorize.get_jwt_subject()
