from fastapi import APIRouter
from .endpoints.users import router as users_router
from .endpoints.documents import router as documents_router
from .endpoints.chat import chat_router
from .endpoints.message import message_router

v1_router = APIRouter()

v1_router.include_router(users_router, prefix="/users", tags=["users"])
v1_router.include_router(
    documents_router, prefix="/chats-doc", tags=["documents"])
v1_router.include_router(chat_router, prefix="/chats", tags=["chats"])
v1_router.include_router(message_router, prefix="/chats", tags=["Messages"])
