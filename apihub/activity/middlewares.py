import json
from typing import Callable, Any
from fastapi import Request
from fastapi_jwt_auth import AuthJWT
from starlette.middleware.base import BaseHTTPMiddleware

from ..common.db_session import db_context
from ..security.schemas import SecurityToken
from .schemas import ActivityBase
from .models import Activity

class ActivityLogger(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def set_body(self, request: Request):
        receive_ = await request._receive()

        async def receive():
            return receive_

        request._receive = receive

    async def dispatch(self, request: Request, call_next):
        data = {
            "ip": request.client.host,
            "user_agent": request.headers.get("User-Agent"),
            "method": request.method,
            "path": request.url.path,
            "headers": dict(request.headers),
            "query_params": request.query_params,
        }

        is_recording = request.url.path.startswith("/async")

        if is_recording:
            await self.set_body(request)
            body = await request.body()
            if body:
                data["request_body"] = body
            
            # get authorization from request
            authorization = request.headers.get('Authorization')
            if authorization:
                auth = AuthJWT(req=request)
                token = SecurityToken.from_token(auth)
                data["user_id"] = token.user_id
        
        # call next middleware
        response = await call_next(request)

        if is_recording:
            # extract response body
            data["response_status_code"] = response.status_code
            try:
                data["response_body"] = json.dumps(await response.json(), encoding='utf-8')
            except Exception as e:
                pass

            try:
                with db_context() as session:
                    activity = ActivityBase(**data)
                    session.add(Activity(**activity.dict()))
            except Exception as e:
                pass
        
        return response


async def log_activity(request: Request, call_next: Callable, session: Any):
    data = {
        "ip": request.client.host,
        "user_agent": request.headers.get("User-Agent"),
        "method": request.method,
        "path": request.url.path,
        "headers": dict(request.headers),
        "query_params": request.query_params,
    }

    is_recording = request.url.path.startswith("/async")

    if is_recording:
        try:
            data["request_body"] = json.dumps(await request.json(), encoding='utf-8')
        except Exception as e:
            pass
        
        # get authorization from request
        authorization = request.headers.get('Authorization')
        if authorization:
            auth = AuthJWT(req=request)
            token = SecurityToken.from_token(auth)
            data["user_id"] = token.user_id
    
    # call next middleware
    response = await call_next(request)

    if is_recording:
        # extract response body
        data["response_status_code"] = response.status_code
        try:
            data["response_body"] = json.dumps(await response.json(), encoding='utf-8')
        except Exception as e:
            pass

        # store activity
        with db_context() as session:
            activity = ActivityBase(**data)
            session.add(Activity(**activity.dict()))
    
    return response