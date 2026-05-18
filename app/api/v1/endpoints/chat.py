from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from datetime import datetime, timezone
from ....models.models import Chat, User, ChatResponse, ChatCreate, ChatUpdate
from ..deps.user_deps import get_current_active_user
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from ....db.database import get_session

chat_router = APIRouter()
AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]


@chat_router.get("/demo")
async def demo_chat():
    return [{"username": "Hello from demo chat Route"}]


@chat_router.post("", response_model=ChatResponse, status_code=201)
async def create_chat(data: ChatCreate, current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):

    chat = Chat(
        title=data.title or "New Chat",
        user_id=current_user.id
    )

    session.add(chat)

    await session.commit()

    await session.refresh(chat)

    return chat


@chat_router.get("", response_model=list[ChatResponse])
async def get_chats(current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):

    chats = (
        await session.exec(
            select(Chat)
            .where(
                Chat.user_id == current_user.id
            )
            .order_by(Chat.updated_at.desc())
        )
    ).all()

    return chats


@chat_router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(chat_id: UUID, current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):

    chat = await session.get(Chat, chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    return chat


@chat_router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(chat_id: UUID, data: ChatUpdate, current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):

    chat = await session.get(Chat, chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    chat.title = data.title

    chat.updated_at = datetime.now(
        timezone.utc
    )

    session.add(chat)

    await session.commit()

    await session.refresh(chat)

    return chat


@chat_router.delete("/{chat_id}", status_code=204)
async def delete_chat(chat_id: UUID, current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):

    chat = await session.get(Chat, chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    await session.delete(chat)

    await session.commit()
