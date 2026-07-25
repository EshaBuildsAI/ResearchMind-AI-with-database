"""
app/routers/query.py
POST /query/chat — the core RAG endpoint. Finds relevant chunks (user-scoped,
across one or several documents), asks GPT-4o-mini for an answer, saves
chat history, returns sources.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import ChatMessage, Document, User
from app.schemas import ChatMessageOut, ChatRequest, ChatResponse
from app.services import guardrails, llm_service, rate_limit, usage_service, vectorstore
from app.services.llm_service import LLMNotConfigured

router = APIRouter(prefix="/query", tags=["query"])


def _resolve_doc_ids(payload: ChatRequest) -> list:
    if payload.document_ids:
        return list(payload.document_ids)
    if payload.document_id:
        return [payload.document_id]
    return []


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("chat", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    usage_service.enforce_daily_limit(db, current_user, "chat")

    is_valid, cleaned_or_error = guardrails.validate_question(payload.question)
    if not is_valid:
        raise HTTPException(400, cleaned_or_error)
    question = cleaned_or_error
    guardrails.check_for_injection_attempt(question)  # logged, warn-only

    doc_ids = _resolve_doc_ids(payload)

    if doc_ids:
        for doc_id in doc_ids:
            document = db.query(Document).filter(
                Document.id == doc_id, Document.user_id == current_user.id
            ).first()
            if not document:
                raise HTTPException(404, f"Document not found: {doc_id}")
            if document.status != "ready":
                raise HTTPException(409, f"Document is still {document.status}. Try again once it's ready.")

        chunks = vectorstore.query(current_user.id, question, doc_id=doc_ids)
        try:
            answer = llm_service.answer_question(question, chunks)
        except LLMNotConfigured as e:
            raise HTTPException(503, str(e))
    else:
        # No document attached — answer like a normal AI assistant from
        # general knowledge, not restricted to any document's content.
        chunks = []
        try:
            answer = llm_service.answer_general_question(question)
        except LLMNotConfigured as e:
            raise HTTPException(503, str(e))

    is_valid_output, answer_or_error = guardrails.validate_ai_output(answer)
    if not is_valid_output:
        raise HTTPException(502, answer_or_error)
    answer = answer_or_error

    primary_doc_id = doc_ids[0] if doc_ids else None
    doc_ids_json = json.dumps(doc_ids) if len(doc_ids) > 1 else None
    db.add(ChatMessage(user_id=current_user.id, document_id=primary_doc_id, document_ids_json=doc_ids_json,
                        role="user", content=question, feature="chat"))
    db.add(ChatMessage(user_id=current_user.id, document_id=primary_doc_id, document_ids_json=doc_ids_json,
                        role="assistant", content=answer, feature="chat"))
    db.commit()
    usage_service.increment_usage(db, current_user.id, "chat")

    return ChatResponse(answer=answer, sources=[{"text": c} for c in chunks])


@router.get("/history", response_model=list[ChatMessageOut])
def chat_history(
    document_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id)
    if document_id:
        q = q.filter(ChatMessage.document_id == document_id)
    messages = q.order_by(ChatMessage.created_at.asc()).all()
    return [
        {
            "id": m.id, "role": m.role, "content": m.content,
            "feature": m.feature, "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]
