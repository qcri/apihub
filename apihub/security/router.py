import datetime
from typing import List
from pydantic import BaseModel, BaseSettings
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi_jwt_auth import AuthJWT

from ..common.db_session import create_session, Base, DB_ENGINE
from .schemas import UserCreate, UserBase, UserRegister, UserType
from .queries import UserQuery, UserException
from .depends import require_token, require_admin, require_app


security = HTTPBasic()
router = APIRouter()

HTTP_403_FORBIDDEN = 403


class SecuritySettings(BaseSettings):
    authjwt_secret_key: str = "secret"
    security_token_expires_time: int = 1


@AuthJWT.load_config
def get_config():
    return SecuritySettings()


class AuthenticateResponse(BaseModel):
    username: str
    roles: List[str]
    access_token: str
    expires_time: int


class SuperUser(BaseSettings):
    username: str
    password: str
    email: str

    def as_usercreate(self):
        return UserCreate(
            username=self.username,
            password=self.password,
            email=self.email,
            role=UserType.ADMIN,
        )


@router.get("/_init")
async def _init(
    session=Depends(create_session),
):
    Base.metadata.bind = DB_ENGINE
    Base.metadata.create_all()

    user = SuperUser().as_usercreate()
    UserQuery(session).create_user(user)


@router.get("/_delete")
async def _delete(
    session=Depends(create_session),
):
    Base.metadata.bind = DB_ENGINE
    Base.metadata.drop_all()


@router.get("/_authenticate")
async def _authenticate(
    credentials: HTTPBasicCredentials = Depends(security),
    session=Depends(create_session),
):
    query = UserQuery(session)
    try:
        user = query.get_user_by_username_and_password(
            username=credentials.username,
            password=credentials.password,
        )
    except UserException:
        raise HTTPException(HTTP_403_FORBIDDEN, "User not found or wrong password")

    roles = [user.role]

    Authorize = AuthJWT()
    expires_days = SecuritySettings().security_token_expires_time
    expires_time = datetime.timedelta(days=expires_days)
    access_token = Authorize.create_access_token(
        subject=user.username,
        user_claims={"roles": roles},
        expires_time=expires_time,
    )
    return AuthenticateResponse(
        username=user.username,
        roles=roles,
        expires_time=expires_time.seconds,
        access_token=access_token,
    )


@router.get("/user/{username}")
async def get_user(
    username: str,
    current_user: UserBase = Depends(require_token),
    session=Depends(create_session),
):
    if current_user.is_admin or current_user.is_manager:
        if username == "me":
            username = current_user.username
    elif username == "me":
        username = current_user.username
    else:
        raise HTTPException(HTTP_403_FORBIDDEN, "You have no permission")

    query = UserQuery(session)
    user = query.get_user_by_username(username=username)
    return UserBase(
        username=user.username,
        role=user.role,
    )


class GetUserAdminIn(BaseModel):
    usernames: str


@router.get("/user")
async def get_user_admin(
    usernames: GetUserAdminIn,
    current_username: str = Depends(require_admin),
    session=Depends(create_session),
):
    query = UserQuery(session)
    users = query.get_users_by_usernames(usernames=usernames.usernames.split(","))
    return [UserBase(**user.dict()) for user in users]


class ChangePasswordIn(BaseModel):
    password: str


@router.post("/user/_password")
async def change_password(
    password: ChangePasswordIn,
    current_user: UserBase = Depends(require_token),
    session=Depends(create_session),
):
    query = UserQuery(session)
    query.change_password(username=current_user.username, password=password.password)


@router.post("/user/{username}")
async def create_user(
    username: str,
    new_user: UserCreate,
    current_username: str = Depends(require_admin),
    session=Depends(create_session),
):
    query = UserQuery(session)
    query.create_user(new_user)
    # TODO handling results
    return {}


@router.post("/user/{username}/_password")
async def change_password_admin(
    username: str,
    password: ChangePasswordIn,
    current_username: str = Depends(require_admin),
    session=Depends(create_session),
):
    query = UserQuery(session)
    query.change_password(username=username, password=password.password)


@router.post("/register")
async def register_user(
    new_user: UserRegister,
    current_username: str = Depends(require_app),
    session=Depends(create_session),
):
    query = UserQuery(session)
    query.create_user(
        UserCreate(
            username=new_user.username,
            email=new_user.email,
            password=new_user.password,
            role=UserType.USER,
        )
    )
    return {}
