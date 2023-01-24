import os
import datetime
import hashlib
from base64 import b64encode, b64decode
from fastapi_jwt_auth import AuthJWT


def hash_password(password, salt=None):
    """
    Hash password with salt.
    :param password: str
    :param salt: salt algorithm to use.
    :return:
    """
    if salt is None:
        salt_ = os.urandom(32)
        salt = b64encode(salt_)
    else:
        salt_ = b64decode(salt)
    hashed_password = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_,
        100000,
        dklen=64,
    ).hex()
    return salt, hashed_password


def make_token(user, expires_time):
    Authorize = AuthJWT()
    access_token = Authorize.create_access_token(
        subject=user.email,
        user_claims={"role": user.role, "name": user.name, "id": user.id},
        expires_time=expires_time,
    )
    return access_token