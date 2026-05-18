import aiofiles
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Depends, File, UploadFile
from ....models.models import User, Document, DocumentResponse
from typing import Annotated
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from ....db.database import get_session
from ....services.vector_db import extract_document_and_save
from ....core.config import Settings, get_settings
from ..deps.user_deps import get_current_active_user, RoleChecker


router = APIRouter()

AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]
settings: Settings = get_settings()
allow_admin = RoleChecker(["admin"])

UPLOAD_DIR = Path("storage/uploads")


@router.get("", response_model=list[DocumentResponse])
async def read_docs(current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):
    docs = (await session.exec(select(Document).where(Document.user_id == current_user.id))).all()

    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document found"
        )

    return docs


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="Upload document")],
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: AsyncSessionDep
):
    allowed_types = [
        "application/pdf",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type"
        )

    user_upload_dir = UPLOAD_DIR / str(current_user.id) / "documents"
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid4()}_{file.filename}"
    file_path = user_upload_dir / unique_filename

    file_size = 0

    async with aiofiles.open(file_path, "wb") as buffer:
        while content := await file.read(1024 * 1024):
            file_size += len(content)
            await buffer.write(content)

    document = Document(
        filename=file.filename,
        file_path=str(file_path),
        file_type=file.content_type,
        file_size=file_size,
        status="uploaded",
        user_id=current_user.id
    )

    current_user_id = str(current_user.id)
    doc_filename = file.filename

    session.add(document)
    await session.commit()
    await session.refresh(document)

    document_id = str(document.id)

    background_tasks.add_task(
        extract_document_and_save,
        str(file_path),
        current_user_id,
        document_id,
        doc_filename
    )

    return {
        "message": "Document uploaded successfully",
        "document_id": document.id,
        "filename": document.filename,
    }


@router.get("/delete{doc_id}")
async def delete_doc(doc_id: str, current_user: Annotated[User, Depends(get_current_active_user)], session: AsyncSessionDep):
    doc = (await session.exec(select(Document).where(Document.user_id == current_user.id and Document.id == doc_id))).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    await session.delete(doc)
    await session.commit()

    return {
        "message": "Document deleted successfully",
    }
