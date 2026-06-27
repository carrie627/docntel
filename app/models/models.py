from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, JSON
from sqlalchemy import Column, DateTime, JSON
from pydantic import EmailStr
from enum import Enum
from sqlalchemy.dialects.postgresql import JSONB


class UserBase(SQLModel):
    username: str = Field(index=True, unique=True, min_length=3, max_length=50)
    email: EmailStr = Field(unique=True, index=True)
    full_name: Optional[str] = None
    is_active: bool = True


class User(UserBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    roles: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    profile_image: str | None = Field(default=None)

    documents: list["Document"] = Relationship(
        back_populates="user", cascade_delete=True)

    chats: list["Chat"] = Relationship(
        back_populates="user",
        cascade_delete=True
    )


class UserCreate(UserBase):
    password: str


class UserPublic(UserBase):
    pass


class UserPrivate(UserBase):
    id: UUID
    profile_image: str | None
    created_at: datetime
    roles: List[str]


class UserUpdate(SQLModel):
    username: str | None = None
    email: EmailStr | None = None
    full_name: str | None = None


class PasswordChange(SQLModel):
    old_password: str
    new_password: str


class UserWithToken(SQLModel):
    user: UserPrivate
    access_token: str
    token_type: str = "bearer"


class DocumentBase(SQLModel):
    filename: str
    content_preview: str | None = None
    file_path: str
    file_type: str
    file_size: int
    status: str = Field(default="uploading")
    progress: int = Field(default=0)

    user_id: UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    chat_id: UUID = Field(foreign_key="chat.id")


class Document(DocumentBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )

    user: User = Relationship(back_populates="documents")
    chat: "Chat" = Relationship(back_populates="documents")


class DocumentResponse(DocumentBase):
    id: UUID


# class ChatBase(SQLModel):
#     title: str = Field(default="New Chat", min_length=3, max_length=200)
#     user_id: UUID = Field(foreign_key="user.id",
#                           ondelete="CASCADE", index=True)


# class Chat(ChatBase, table=True):
#     id: UUID = Field(default_factory=uuid4, primary_key=True)
#     messages: list["Message"] = Relationship(back_populates="chat")

#     user: User = Relationship(back_populates="chats")

#     created_at: datetime = Field(
#         sa_column=Column(DateTime(timezone=True), nullable=False),
#         default_factory=lambda: datetime.now(timezone.utc)
#     )

class ChatBase(SQLModel):

    title: str = Field(
        default="New Chat",
        min_length=3,
        max_length=200
    )


class Chat(ChatBase, table=True):

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True
    )

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False
        ),
        default_factory=lambda:
            datetime.now(timezone.utc)
    )

    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False
        ),
        default_factory=lambda:
            datetime.now(timezone.utc)
    )

    user_id: UUID = Field(
        foreign_key="user.id",
        ondelete="CASCADE",
        index=True
    )

    messages: list["Message"] = Relationship(
        back_populates="chat",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan"
        }
    )

    user: "User" = Relationship(
        back_populates="chats"
    )

    documents: list["Document"] = Relationship(back_populates="chat", sa_relationship_kwargs={
        "cascade": "all, delete-orphan"
    })


class ChatCreate(SQLModel):
    title: str | None = "New Chat"


class ChatResponse(SQLModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatUpdate(SQLModel):
    title: str


class SourceItem(SQLModel):
    doc_id: str
    source: str
    page: str


class MessageBase(SQLModel):

    role: str

    content: str

    sources: Optional[List[SourceItem]] = Field(
        default=None, sa_column=Column(JSONB))

    chat_id: UUID = Field(
        foreign_key="chat.id",
        ondelete="CASCADE",
        index=True
    )


class Message(MessageBase, table=True):

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True
    )

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False
        ),
        default_factory=lambda:
            datetime.now(timezone.utc)
    )

    chat: "Chat" = Relationship(
        back_populates="messages"
    )


class MessageCreate(SQLModel):
    role: str = "user"
    content: str = Field(
        min_length=1
    )


class MessageResponse(SQLModel):
    id: UUID
    role: str
    content: str
    sources: Optional[List[SourceItem]]
    created_at: datetime

# class MessageBase(SQLModel):
#     role: str
#     content: str
#     sources: Optional[str] = None

#     chat_id: UUID = Field(foreign_key="chat.id", ondelete="CASCADE")


# class Message(MessageBase, table=True):
#     id: UUID = Field(default_factory=uuid4, primary_key=True)
#     chat: Chat = Relationship(back_populates="messages")


class Token(SQLModel):
    access_token: str
    token_type: str


class TokenData(SQLModel):
    username: str | None = None
