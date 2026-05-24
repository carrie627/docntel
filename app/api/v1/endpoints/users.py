import aiofiles
from pathlib import Path
from uuid import uuid4
from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Depends, Query, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import selectinload
from ....models.models import UserCreate, UserWithToken, User, UserPrivate, Token, UserUpdate, PasswordChange
from typing import Annotated
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from ....db.database import get_session
from ....core.config import Settings, get_settings
from ..deps.user_deps import get_current_user, get_current_active_user, get_user, oauth2_scheme, RoleChecker
from ..auth import get_password_hash, authenticate_user, create_access_token, verify_password


router = APIRouter()

AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]
settings: Settings = get_settings()
allow_admin = RoleChecker(["admin"])

UPLOAD_DIR = Path("storage/uploads")


@router.get("", response_model=list[UserPrivate], dependencies=[Depends(allow_admin)])
async def get_all_users(session: AsyncSessionDep, offset: int = 0, limit: Annotated[int, Query(le=10)] = 10):
    users = (await session.exec(select(User).offset(offset).limit(limit))).all()

    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found"
        )

    return users


@router.get("/me", response_model=UserPrivate)
async def get_user_me(current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):
    statement = (
        select(User)
        .where(User.id == current_user.id)
    )

    user = (await session.exec(statement)).first()

    return user


@router.patch("/me", response_model=UserPrivate)
async def update_my_info(data: UserUpdate, current_user: Annotated[User, Depends(get_current_user)], session: AsyncSessionDep):
    user_data = data.model_dump(exclude_unset=True)

    if "username" in user_data:
        statement = select(User).where(
            User.username == user_data["username"], User.id != current_user.id)
        result = await session.exec(statement)
        if result.first():
            raise HTTPException(
                status_code=400, detail="Username already exists")

    if "email" in user_data:
        statement = select(User).where(
            User.email == user_data["email"], User.id != current_user.id)
        result = await session.exec(statement)
        if result.first():
            raise HTTPException(
                status_code=400, detail="Email already exists")

    for key, value in user_data.items():
        setattr(current_user, key, value)

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return current_user


@router.patch("/me/image")
async def update_my_image(file: Annotated[UploadFile, File(description="A profile picture")], current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):
    # Validate file type
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPG or PNG image allowed"
        )

    if current_user.profile_image:
        old_path = Path(current_user.profile_image)
        if old_path.exists():
            old_path.unlink()

    user_upload_dir = UPLOAD_DIR / str(current_user.id) / "profile_pic"
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    file_extension = file.filename.split(".")[-1]
    filename = f"user_{current_user.id}_{uuid4()}.{file_extension}"
    file_path = user_upload_dir / filename

    async with aiofiles.open(file_path, "wb") as buffer:
        while content := await file.read(1024 * 1024):
            await buffer.write(content)

    # Update database
    current_user.profile_image = str(file_path)
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return {"message": "Image saved", "image_url": current_user.profile_image}


@router.delete("/me/image")
async def delete_my_image(current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):
    if not current_user.profile_image:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image found"
        )

    if current_user.profile_image:
        path = Path(current_user.profile_image)
        if path.exists():
            path.unlink()

    current_user.profile_image = None
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return {"message": "Image deleted."}


@router.post("/me/change-password")
async def change_my_password(data: PasswordChange, current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):
    if not data.old_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please provide the old password first"
        )

    # Check if old password is given
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incorrect old password"
        )

    # Check if new password match the old password
    if verify_password(data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="New password is same as old password"
        )

    current_user.hashed_password = get_password_hash(data.new_password)

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return {"message": "Password changed"}


@router.get("/create")
async def create_user(token: Annotated[str, Depends(oauth2_scheme)]):
    return token


@router.post("/create")
async def create_user(user: UserCreate, session: AsyncSessionDep):
    statement = select(User).where(User.username == user.username)
    result = await session.exec(statement)
    existing_user = result.first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    hashed_password = get_password_hash(user.password)

    new_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
    )

    access_token_expires = timedelta(
        minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": new_user.username},
        expires_delta=access_token_expires,
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    response = JSONResponse(
        content={
            "message": "Sign up successful",
            "user": new_user,
        }
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        # Change httponly to true in production. Now false for postman test
        httponly=False,
        secure=False,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/"
    )

    return response

    # return {
    #     "user": new_user,
    #     "access_token": access_token,
    #     "token_type": "bearer"
    # }


@router.get("/{user_id}", response_model=UserPrivate, dependencies=[Depends(allow_admin)])
async def get_user_by_id(user_id: str, session: AsyncSessionDep):
    user = await session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.post("/token")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: AsyncSessionDep):

    userObj = await get_user(form_data.username, session)
    user = await authenticate_user(userObj, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(
        minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires,
    )

    response = JSONResponse(
        content={
            "message": "Login successful"
        }
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        # Change httponly to true in production. Now false for postman test
        httponly=False,
        secure=False,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60
    )

    return response


@router.delete("/me")
async def delete_me(current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await session.delete(current_user)
    await session.commit()

    return {"message": "Deleted successfully"}


@router.delete("/{user_id}", dependencies=[Depends(allow_admin)])
async def delete_user(user_id: str, session: AsyncSessionDep):
    target_user = await session.get(User, user_id)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await session.delete(target_user)
    await session.commit()

    return {"message": "User deleted successfully"}


@router.post("/logout")
async def logout():

    response = JSONResponse(
        content={
            "message": "Logged out"
        }
    )

    response.delete_cookie(
        "access_token"
    )

    return response
