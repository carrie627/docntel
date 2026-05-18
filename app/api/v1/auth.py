from datetime import datetime, timezone, timedelta
from pwdlib import PasswordHash
import jwt
from jwt.exceptions import InvalidTokenError
from ...core.config import get_settings, Settings
from fastapi.security import OAuth2PasswordBearer
from ...models.models import User

settings: Settings = get_settings()

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/token")


def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


async def authenticate_user(user: User, password: str):
    if not user:
        verify_password(password, DUMMY_HASH)
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key.get_secret_value(), algorithm=settings.algorithm)
    return encoded_jwt


def verify_access_token(token: str) -> str | None:
    """Verify the access token and return the subject if valid"""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
        )
    except InvalidTokenError:
        return None
    else:
        username = payload.get("sub")
        return username
