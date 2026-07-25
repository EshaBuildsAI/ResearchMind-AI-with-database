"""
app/routers/features.py
The standalone AI features (not multi-step agents): Summary, Quiz,
Flashcards, Literature Review, Research Gap Finder, Presentation outline,
Proposal Generator, and Smart Memory (read-only view of stored Q&A history).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Document, User
from app.schemas import (
    FlashcardRequest, PresentationRequest, ProposalRequest, QuizRequest, SummaryRequest,
)
from app.services import guardrails, llm_service, memory_service, rate_limit, vectorstore
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
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    result = _run(llm_service.generate_summary, text, payload.length)
    valid, result_or_error = guardrails.validate_ai_output(result)
    if not valid:
        raise HTTPException(502, result_or_error)
    return {"summary": result_or_error}


@router.post("/quiz")
def quiz(payload: QuizRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("features", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    questions = _run(llm_service.generate_quiz, text, payload.num_questions)
    if not questions:
        raise HTTPException(502, "Couldn't generate a valid quiz from this document. Try again.")
    return {"questions": questions}


@router.post("/flashcards")
def flashcards(payload: FlashcardRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("features", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    cards = _run(llm_service.generate_flashcards, text, payload.num_cards)
    if not cards:
        raise HTTPException(502, "Couldn't generate flashcards from this document. Try again.")
    return {"cards": cards}


@router.post("/literature-review")
def literature_review(payload: SummaryRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("features", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    result = _run(llm_service.generate_literature_review, text)
    return {"literature_review": result}


@router.post("/research-gap")
def research_gap(payload: SummaryRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("features", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    result = _run(llm_service.detect_research_gaps, text)
    return {"research_gaps": result}


@router.post("/presentation")
def presentation(payload: PresentationRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("features", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    slides = _run(llm_service.generate_presentation_outline, text, payload.num_slides)
    if not slides:
        raise HTTPException(502, "Couldn't generate a presentation outline from this document. Try again.")
    return {"slides": slides}


@router.post("/proposal")
def proposal(payload: ProposalRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("features", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    text = _get_ready_document_text(db, current_user.id, payload.document_id)
    result = _run(llm_service.generate_proposal, text, payload.degree_level, payload.university)
    return {"proposal": result}


@router.get("/smart-memory/{document_id}")
def smart_memory(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(404, "Document not found.")
    return {"entries": memory_service.load_memory(db, current_user.id, document_id)}
