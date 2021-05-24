import os
import hashlib
from base64 import b64encode, b64decode


def hash_password(password, salt=None):
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
    ).hex()
    return salt, hashed_password
