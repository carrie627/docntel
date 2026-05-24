from fastapi import HTTPException, status, Depends, Request, WebSocket, WebSocketException
from fastapi.security import OAuth2PasswordBearer
from ....models.models import TokenData, User
from typing import Annotated, List
from sqlmodel.ext.asyncio.session import AsyncSession
from ....db.database import get_session
from ..auth import verify_access_token
from sqlmodel import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/token")
AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_user(username: str, session: AsyncSessionDep):
    statement = select(User).where(User.username == username)
    result = await session.exec(statement)
    user = result.first()

    if user:
        return user


# THIS IS FOR PASSWORD BEARER TOKEN NOT FOR COOKIE BASED AUTH
# async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: AsyncSessionDep):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"}
#     )

#     username = verify_access_token(token)

#     if username is None:
#         raise credentials_exception
#     token_data = TokenData(username=username)
#     user = await get_user(token_data.username, session)
#     if user is None:
#         raise credentials_exception
#     return user

async def get_current_user(request: Request, session: AsyncSessionDep):
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    username = verify_access_token(token=token)
    user = await get_user(username, session)
    return user


async def get_current_user_ws(websocket: WebSocket, session: AsyncSessionDep):
    print("dependency hit")
    # token = websocket.cookies.get("access_token")
    token = websocket.cookies["access_token"]
    print("Access token: ", token)

    if not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Not authenticated",
        )

    username = verify_access_token(token)
    if username is None:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid token.",
        )

    user = await get_user(username, session)
    if not user:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="User not found",
        )

    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Annotated[User, Depends(get_current_user)]):
        if not any(role in self.allowed_roles for role in current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have enough permissions"
            )

        return current_user
