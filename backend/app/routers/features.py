"""
app/routers/features.py
The standalone AI features (not multi-step agents): Summary, Quiz,
Flashcards, Literature Review, Research Gap Finder, Presentation outline,
Proposal Generator, and Smart Memory (read-only view of stored Q&A history).
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Document, User
from app.schemas import (
    FlashcardRequest, PresentationRequest, ProposalRequest, QuizRequest, SummaryRequest,
)
<<<<<<< HEAD
from app.services import guardrails, llm_service, memory_service, pptx_generator, rate_limit, usage_service, vectorstore
=======
from app.services import guardrails, llm_service, memory_service, rate_limit, usage_service, vectorstore
>>>>>>> 534d3e68cf165288c34e4a62b43a2afab8657a38
from app.services.llm_service import LLMNotConfigured

router = APIRouter(prefix="/features", tags=["features"])


def _get_ready_document_text(db: Session, user_id: str, document_id: str) -> str:
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if not document:
        raise HTTPException(404, "Document not found.")
    if document.status != "ready":
        raise HTTPException(409, f"Document is still {document.status}. Try again once it's ready.")
    text = vectorstore.get_full_document_text(user_id, document_id)
    if not text:
        raise HTTPException(404, "No extracted text found for this document.")
    return text


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))


@router.post("/summary")
def summary(payload: SummaryRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("features", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    usage_service.enforce_daily_limit(db, current_user, "chat")
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    result = _run(llm_service.generate_summary, text, payload.length)
    valid, result_or_error = guardrails.validate_ai_output(result)
    if not valid:
        raise HTTPException(502, result_or_error)
    return {"summary": result_or_error}


@router.post("/quiz")
def quiz(payload: QuizRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("features", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    usage_service.enforce_daily_limit(db, current_user, "chat")
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    questions = _run(llm_service.generate_quiz, text, payload.num_questions)
    if not questions:
        raise HTTPException(502, "Couldn't generate a valid quiz from this document. Try again.")
    return {"questions": questions}


@router.post("/flashcards")
def flashcards(payload: FlashcardRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("features", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    usage_service.enforce_daily_limit(db, current_user, "chat")
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    cards = _run(llm_service.generate_flashcards, text, payload.num_cards)
    if not cards:
        raise HTTPException(502, "Couldn't generate flashcards from this document. Try again.")
    return {"cards": cards}


@router.post("/literature-review")
def literature_review(payload: SummaryRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("features", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    usage_service.enforce_daily_limit(db, current_user, "chat")
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    result = _run(llm_service.generate_literature_review, text)
    return {"literature_review": result}


@router.post("/research-gap")
def research_gap(payload: SummaryRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("features", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    usage_service.enforce_daily_limit(db, current_user, "chat")
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    result = _run(llm_service.detect_research_gaps, text)
    return {"research_gaps": result}


@router.post("/presentation")
def presentation(payload: PresentationRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("features", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    usage_service.enforce_daily_limit(db, current_user, "chat")
<<<<<<< HEAD
    document = db.query(Document).filter(Document.id == payload.document_id, Document.user_id == current_user.id).first()
=======
>>>>>>> 534d3e68cf165288c34e4a62b43a2afab8657a38
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    slides = _run(llm_service.generate_presentation_outline, text, payload.num_slides)
    if not slides:
        raise HTTPException(502, "Couldn't generate a presentation outline from this document. Try again.")

    deck_title = (document.filename.rsplit(".", 1)[0] if document else "Presentation").replace("_", " ")
    try:
        file_path = pptx_generator.build_presentation(deck_title, slides)
        file_id = os.path.basename(file_path)
    except Exception:
        file_id = None  # slide content still returned even if the .pptx build itself fails

    return {"slides": slides, "file_id": file_id}


@router.get("/presentation/download/{file_id}")
def download_presentation(file_id: str, request: Request, token: str | None = None, db: Session = Depends(get_db)):
    """Downloads the generated .pptx. Accepts the access token via query
    param too (same pattern as the document file-serve endpoint) since a
    plain download link can't send an Authorization header."""
    from app.core.deps import get_user_from_token_string

    auth_header = request.headers.get("authorization", "")
    bearer_token = auth_header[7:] if auth_header.startswith("Bearer ") else token
    current_user = get_user_from_token_string(bearer_token, db) if bearer_token else None
    if not current_user:
        raise HTTPException(401, "Authentication required.")

    # file_id is a bare UUID-based filename (no path segments) generated by
    # this server, so this is safe from path traversal, but validate anyway.
    safe_id = os.path.basename(file_id)
    file_path = os.path.join(settings.EXPORT_DIR, safe_id)
    if not safe_id.endswith(".pptx") or not os.path.exists(file_path):
        raise HTTPException(404, "That presentation file was not found — it may have expired.")

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename="presentation.pptx",
    )


@router.post("/proposal")
def proposal(payload: ProposalRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("features", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    usage_service.enforce_daily_limit(db, current_user, "chat")
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    result = _run(llm_service.generate_proposal, text, payload.degree_level, payload.university)
    return {"proposal": result}


@router.get("/smart-memory/{document_id}")
def smart_memory(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(404, "Document not found.")
    return {"entries": memory_service.load_memory(db, current_user.id, document_id)}