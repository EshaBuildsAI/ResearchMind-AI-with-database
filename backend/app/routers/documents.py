"""
app/routers/documents.py
Upload responds immediately; text extraction + embedding runs in the
background (FastAPI BackgroundTasks — a single-process queue, documented
honestly in the roadmap as not a true distributed queue like Celery+Redis).
"""

import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.models import ChatMessage, Document, User
from app.schemas import DocumentOut
from app.services import document_processor, vectorstore
from app.utils.text import ensure_dir, get_file_extension, is_file_size_valid, safe_filename

logger = logging.getLogger("researchmind")
router = APIRouter(prefix="/documents", tags=["documents"])

ensure_dir(settings.UPLOAD_DIR)


def _process_document_background(document_id: str, user_id: str, storage_path: str, filename: str):
    """Runs after the upload response is already sent. Uses its own DB
    session since the request-scoped one is closed by the time this runs."""
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return

        document.status = "processing"
        db.commit()

        with open(storage_path, "rb") as f:
            file_bytes = f.read()

        result = document_processor.process_document(filename, file_bytes)
        chunk_count = vectorstore.add_document(
            user_id=user_id, doc_id=document_id, filename=filename,
            text=result["text"], pages=result["pages"],
        )

        document.status = "ready"
        document.chunk_count = chunk_count
        db.commit()
        logger.info(f"Document {document_id} processed: {chunk_count} chunks.")
    except Exception as e:
        logger.exception(f"Document {document_id} processing failed: {e}")
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = "failed"
                document.error_message = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/upload", response_model=DocumentOut, status_code=201)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services import usage_service
    usage_service.enforce_document_limit(db, current_user)

    extension = get_file_extension(file.filename)
    if extension not in settings.SUPPORTED_FORMATS:
        raise HTTPException(400, f"Unsupported file type '.{extension}'. "
                                  f"Supported: {', '.join(settings.SUPPORTED_FORMATS)}")

    file_bytes = file.file.read()
    if not is_file_size_valid(file_bytes, settings.MAX_FILE_SIZE_MB):
        raise HTTPException(400, f"File too large. Max size is {settings.MAX_FILE_SIZE_MB}MB.")

    document_id = str(uuid.uuid4())
    ensure_dir(os.path.join(settings.UPLOAD_DIR, current_user.id))
    storage_path = os.path.join(
        settings.UPLOAD_DIR, current_user.id, f"{document_id}_{safe_filename(file.filename)}"
    )
    with open(storage_path, "wb") as f:
        f.write(file_bytes)

    document = Document(
        id=document_id, user_id=current_user.id, filename=file.filename,
        file_type=extension, storage_path=storage_path, status="uploaded",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    background_tasks.add_task(
        _process_document_background, document_id, current_user.id, storage_path, file.filename
    )

    return _serialize(document)


@router.get("", response_model=list[DocumentOut])
def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.created_at.desc()).all()
    return [_serialize(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = db.query(Document).filter(
        Document.id == document_id, Document.user_id == current_user.id
    ).first()
    if not document:
        raise HTTPException(404, "Document not found.")
    return _serialize(document)


@router.get("/{document_id}/file")
def get_document_file(
    document_id: str,
    request: Request,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    """Serves the original uploaded file — used by the Citation Agent's
    'View source' button to open the document in a new tab. A plain link
    opened in a new tab can't send an Authorization header, so this route
    also accepts the access token as a `?token=` query param (same pattern
    as the WebSocket auth in routers/ws.py) alongside the normal header."""
    from app.core.deps import get_user_from_token_string

    auth_header = request.headers.get("authorization", "")
    bearer_token = auth_header[7:] if auth_header.startswith("Bearer ") else token
    current_user = get_user_from_token_string(bearer_token, db) if bearer_token else None
    if not current_user:
        raise HTTPException(401, "Authentication required.")

    document = db.query(Document).filter(
        Document.id == document_id, Document.user_id == current_user.id
    ).first()
    if not document:
        raise HTTPException(404, "Document not found.")
    if not os.path.exists(document.storage_path):
        raise HTTPException(404, "The original file is no longer available on disk.")

    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "txt": "text/plain",
    }
    return FileResponse(
        document.storage_path,
        media_type=media_types.get(document.file_type, "application/octet-stream"),
        filename=document.filename,
    )


@router.delete("/{document_id}")
def delete_document(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = db.query(Document).filter(
        Document.id == document_id, Document.user_id == current_user.id
    ).first()
    if not document:
        raise HTTPException(404, "Document not found.")

    vectorstore.delete_document(current_user.id, document_id)
    db.query(ChatMessage).filter(ChatMessage.document_id == document_id).delete()
    # AgentRun rows referencing this document must go too, or the delete
    # below fails with a foreign-key violation (found via real testing).
    from app.models import AgentRun
    db.query(AgentRun).filter(AgentRun.document_id == document_id).delete()
    db.commit()

    try:
        if os.path.exists(document.storage_path):
            os.remove(document.storage_path)
    except OSError:
        pass

    db.delete(document)
    db.commit()
    return {"message": "Document and all associated data deleted."}


def _serialize(document: Document) -> dict:
    return {
        "id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "status": document.status,
        "chunk_count": document.chunk_count,
        "error_message": document.error_message,
        "created_at": document.created_at.isoformat(),
    }