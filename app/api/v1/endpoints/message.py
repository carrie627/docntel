from fastapi import APIRouter
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketException, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from uuid import UUID
from datetime import datetime, timezone
from ....models.models import Message, MessageCreate, MessageResponse, User, Chat
from ..deps.user_deps import get_current_active_user, get_current_user_ws
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from ....db.database import get_session
from ....services.vector_db import search_documents
from ....services.llm import build_context, build_rag_prompt, stream_ai_response
import time

message_router = APIRouter()
AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]


@message_router.get("/{chat_id}/messages", response_model=list[MessageResponse])
async def get_messages(chat_id: UUID, current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):
    chat = (await session.exec(select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id))).first()

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    messages = (
        await session.exec(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.asc())
        )
    ).all()

    return messages


@message_router.post("/{chat_id}/messages", response_model=MessageResponse)
async def create_message(chat_id: UUID, data: MessageCreate, current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):
    chat = (await session.exec(select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id))).first()

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    message = Message(
        role="user",
        content=data.content,
        chat_id=chat_id,
    )

    session.add(message)
    chat.updated_at = datetime.now(
        timezone.utc
    )

    await session.commit()
    await session.refresh(message)

    # This route is not completed. still have to work here.

    return message


@message_router.get("/{chat_id}/messages-ui")
async def create_message(chat_id: UUID):
    html = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>Chat</title>
        </head>
        <body>
            <h1>WebSocket Chat</h1>

            <form onsubmit="sendMessage(event)">
                <input
                    type="text"
                    id="messageText"
                    autocomplete="off"
                />

                <button>Send</button>
            </form>

            <ul id="messages"></ul>

            <script>

                const ws = new WebSocket(
                    "ws://localhost:8000/api/v1/messages/ws/{chat_id}"
                );

                ws.onmessage = function(event) {{

                    const messages =
                        document.getElementById("messages");

                    const message =
                        document.createElement("li");

                    const content =
                        document.createTextNode(event.data);

                    message.appendChild(content);

                    messages.appendChild(message);
                }};

                function sendMessage(event) {{

                    const input =
                        document.getElementById("messageText");

                    ws.send(input.value);

                    input.value = "";

                    event.preventDefault();
                }}

            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


@message_router.websocket("/ws/{chat_id}")
async def websocket_chat(
    websocket: WebSocket,
    chat_id: UUID,
    current_user: Annotated[User, Depends(get_current_user_ws)],
    session: AsyncSessionDep
):

    await websocket.accept()
    current_user_id = current_user.id

    try:
        while True:
            question = await websocket.receive_text()

            chat = (await session.exec(select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user_id))).first()
            if not chat:
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Chat not found",
                )

            message = Message(
                role="user",
                content=question,
                chat_id=chat_id,
            )

            session.add(message)
            chat.updated_at = datetime.now(
                timezone.utc
            )

            await session.commit()
            await session.refresh(message)

            results = await search_documents(question, current_user_id)

            context = build_context(results)

            prompt = build_rag_prompt(context=context, question=question)

            full_response = ""

            async for token in stream_ai_response(prompt):
                full_response += token

                await websocket.send_text(token)

            await websocket.send_text("[done]")

            assistant_message = Message(
                role="assistant",
                content=full_response,
                chat_id=chat_id,
            )

            session.add(assistant_message)
            await session.commit()
    except WebSocketDisconnect:
        print("Client Disconnected")
