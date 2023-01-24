import datetime
from typing import List
from pydantic import BaseModel, BaseSettings
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi_jwt_auth import AuthJWT

from ..common.db_session import create_session
from .schemas import UserCreate, UserBase, UserRegister, UserType
from .queries import UserQuery, UserException
from .depends import require_token, require_admin, require_app
from .helpers import make_token


security = HTTPBasic()
router = APIRouter()

HTTP_403_FORBIDDEN = 403


class SecuritySettings(BaseSettings):
    authjwt_secret_key: str = "secret"
    security_token_expires_time: int = 30


@AuthJWT.load_config
def get_config():
    return SecuritySettings()


class AuthenticateResponse(BaseModel):
    email: str
    role: str
    access_token: str
    expires_time: int


@router.get("/_authenticate")
async def _authenticate(
    credentials: HTTPBasicCredentials = Depends(security),
    expires_days: int = 1,
    session=Depends(create_session),
):
    query = UserQuery(session)
    try:
        user = query.get_user_by_email_and_password(
            email=credentials.username,
            password=credentials.password,
        )
    except UserException:
        raise HTTPException(HTTP_403_FORBIDDEN, "User not found or wrong password")

    # make sure the max expires_days won't exceed setting
    if expires_days > SecuritySettings().security_token_expires_time:
        expires_days = SecuritySettings().security_token_expires_time

    expires_time = datetime.timedelta(days=expires_days)

    Authorize = AuthJWT()
    access_token = make_token(user, expires_time)
    return AuthenticateResponse(
        email=user.email,
        role=user.role,
        expires_time=expires_time.seconds,
        access_token=access_token,
    )


@router.get("/user")
async def get_user(
    user: UserBase = Depends(require_token),
    session=Depends(create_session),
):
    query = UserQuery(session)
    user = query.get_user_by_email(email=user.email)
    return UserBase(
        name=user.name,
        email=user.email,
        role=user.role,
    )


class GetUserAdminIn(BaseModel):
    emails: str


@router.get("/user")
async def get_user_admin(
    group: GetUserAdminIn,
    admin: str = Depends(require_admin),
    session=Depends(create_session),
):
    query = UserQuery(session)
    users = query.get_users_by_emails(emails=group.emails.split(","))
    return [UserBase(**user.dict()) for user in users]


class ChangePasswordIn(BaseModel):
    password: str


@router.post("/user/_password")
async def change_password(
    password: ChangePasswordIn,
    user: UserBase = Depends(require_token),
    session=Depends(create_session),
):
    query = UserQuery(session)
    query.change_password(email=user.email, password=password.password)


@router.post("/user")
async def create_user(
    user: UserCreate,
    admin: str = Depends(require_admin),
    session=Depends(create_session),
):
    query = UserQuery(session)
    query.create_user(user)
    # TODO handling results
    return {}


@router.get("/users/{role}")
async def list_users(
    role: str,
    admin: str = Depends(require_admin),
    session=Depends(create_session),
):
    query = UserQuery(session)
    users = query.get_users_by_role(role)
    return users


@router.post("/user/{email}/_password")
async def change_password_admin(
    email: str,
    password: ChangePasswordIn,
    admin: str = Depends(require_admin),
    session=Depends(create_session),
):
    query = UserQuery(session)
    query.change_password(email=email, password=password.password)


@router.post("/register")
async def register_user(
    user: UserRegister,
    app: str = Depends(require_app),   # FIXME
    session=Depends(create_session),
):
    query = UserQuery(session)
    query.create_user(
        UserCreate(
            name=user.name,
            email=user.email,
            password=user.password,
            role=UserType.USER,
        )
    )
    return {}
