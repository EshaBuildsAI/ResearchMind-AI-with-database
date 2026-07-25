"""
app/routers/agents.py
Every agent endpoint returns the same AgentRunOut shape (steps + final
result) so the React side panel can render any agent with one component.

Document + topic-text are independent inputs on every agent except
Citation (which genuinely needs a document for page numbers): a request
needs at least ONE of them, and if a document is given but no topic text,
the topic is auto-extracted from the document.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import AgentRun, Document, User
from app.schemas import AgentRequest, AgentRunOut, SummarizeReferenceRequest
from app.services import agent_service, guardrails, llm_service, rate_limit, vectorstore
from app.services.llm_service import LLMNotConfigured

router = APIRouter(prefix="/agents", tags=["agents"])


def _validate_document(db: Session, user_id: str, document_id: str | None) -> Document | None:
    if not document_id:
        return None
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if not document:
        raise HTTPException(404, "Document not found.")
    if document.status != "ready":
        raise HTTPException(409, f"Document is still {document.status}. Try again once it's ready.")
    return document


def _resolve_question_or_topic(db: Session, user_id: str, payload: AgentRequest, require_document: bool = False) -> str:
    """Every agent (except Citation) accepts a document, a topic/question, or
    both. If a document is given but no text, the topic is auto-extracted
    from the document itself. Raises 400 only if genuinely nothing usable
    was provided."""
    document = _validate_document(db, user_id, payload.document_id)
    if require_document and not document:
        raise HTTPException(400, "This agent needs a document — select one and try again.")

    question = (payload.question or "").strip()
    if question:
        is_valid, cleaned_or_error = guardrails.validate_question(question)
        if not is_valid:
            raise HTTPException(400, cleaned_or_error)
        guardrails.check_for_injection_attempt(cleaned_or_error)
        return cleaned_or_error

    if document:
        try:
            doc_text = vectorstore.get_full_document_text(user_id, payload.document_id)
            topic = llm_service.extract_topic(doc_text) if doc_text else ""
        except LLMNotConfigured:
            raise
        except Exception:
            topic = ""
        if topic:
            return topic

    raise HTTPException(400, "Provide a topic/question, select a document, or both.")


def _serialize_run(run: AgentRun) -> dict:
    return {
        "id": run.id,
        "agent_type": run.agent_type,
        "question": run.question,
        "status": run.status,
        "result_text": run.result_text,
        "result": json.loads(run.result_json) if run.result_json else None,
        "error_message": run.error_message,
        "created_at": run.created_at.isoformat(),
        "steps": [
            {
                "step_index": s.step_index, "name": s.name, "label": s.label,
                "status": s.status, "detail": json.loads(s.detail_json) if s.detail_json else None,
            }
            for s in run.steps
        ],
    }


@router.post("/research", response_model=AgentRunOut)
def research_agent(payload: AgentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("agent", current_user.id, settings.AGENT_RATE_LIMIT_PER_MINUTE)
    question = _resolve_question_or_topic(db, current_user.id, payload)
    try:
        run = agent_service.run_research_agent(db, current_user.id, payload.document_id, question)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    return _serialize_run(run)


@router.post("/planner", response_model=AgentRunOut)
def planner_agent(payload: AgentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("agent", current_user.id, settings.AGENT_RATE_LIMIT_PER_MINUTE)
    question = _resolve_question_or_topic(db, current_user.id, payload)
    try:
        topic = ""
        if payload.document_id:
            doc_text = vectorstore.get_full_document_text(current_user.id, payload.document_id)
            topic = llm_service.extract_topic(doc_text) if doc_text else ""
    except Exception:
        topic = ""
    try:
        run = agent_service.run_planner_agent(db, current_user.id, payload.document_id, question, topic=topic or question)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    return _serialize_run(run)


@router.post("/recommendation", response_model=AgentRunOut)
def recommendation_agent(payload: AgentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("agent", current_user.id, settings.AGENT_RATE_LIMIT_PER_MINUTE)
    topic = _resolve_question_or_topic(db, current_user.id, payload)
    try:
        run = agent_service.run_recommendation_agent(db, current_user.id, payload.document_id, topic)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    return _serialize_run(run)


@router.post("/timeline", response_model=AgentRunOut)
def timeline_agent(payload: AgentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("agent", current_user.id, settings.AGENT_RATE_LIMIT_PER_MINUTE)
    topic = _resolve_question_or_topic(db, current_user.id, payload)
    try:
        run = agent_service.run_timeline_agent(db, current_user.id, payload.document_id, topic)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    return _serialize_run(run)


@router.post("/innovation", response_model=AgentRunOut)
def innovation_agent(payload: AgentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("agent", current_user.id, settings.AGENT_RATE_LIMIT_PER_MINUTE)
    topic = _resolve_question_or_topic(db, current_user.id, payload)
    try:
        gaps = ""
        if payload.document_id:
            doc_text = vectorstore.get_full_document_text(current_user.id, payload.document_id)
            gaps = llm_service.detect_research_gaps(doc_text) if doc_text else ""
        run = agent_service.run_innovation_agent(db, current_user.id, payload.document_id, gaps, topic)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    return _serialize_run(run)


@router.post("/citation", response_model=AgentRunOut)
def citation_agent(payload: AgentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rate_limit.enforce("agent", current_user.id, settings.AGENT_RATE_LIMIT_PER_MINUTE)
    if not payload.document_id:
        raise HTTPException(400, "The Citation Agent needs a document — it can't point to a page number without one.")
    _validate_document(db, current_user.id, payload.document_id)
    question = payload.question.strip()
    is_valid, cleaned_or_error = guardrails.validate_question(question)
    if not is_valid:
        raise HTTPException(400, cleaned_or_error)
    guardrails.check_for_injection_attempt(cleaned_or_error)
    try:
        run = agent_service.run_citation_agent(db, current_user.id, payload.document_id, cleaned_or_error)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    return _serialize_run(run)


@router.post("/summarize-reference", response_model=AgentRunOut)
def summarize_reference(
    payload: SummarizeReferenceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tool for the 'summarize this link' feature — any reference card any
    agent surfaced can be sent here to get fetched + summarized."""
    rate_limit.enforce("agent", current_user.id, settings.AGENT_RATE_LIMIT_PER_MINUTE)
    if not payload.url or not payload.url.startswith(("http://", "https://")):
        raise HTTPException(400, "A valid http(s) URL is required.")
    try:
        run = agent_service.run_summarize_reference(
            db, current_user.id, payload.document_id, payload.url, payload.question or ""
        )
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    return _serialize_run(run)


@router.get("/runs", response_model=list[AgentRunOut])
def list_runs(
    document_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(AgentRun).filter(AgentRun.user_id == current_user.id)
    if document_id:
        q = q.filter(AgentRun.document_id == document_id)
    runs = q.order_by(AgentRun.created_at.desc()).limit(50).all()
    return [_serialize_run(r) for r in runs]


@router.get("/runs/{run_id}", response_model=AgentRunOut)
def get_run(run_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = db.query(AgentRun).filter(AgentRun.id == run_id, AgentRun.user_id == current_user.id).first()
    if not run:
        raise HTTPException(404, "Agent run not found.")
    return _serialize_run(run)


@router.delete("/runs/{run_id}")
def delete_run(run_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deleted = agent_service.delete_run(db, current_user.id, run_id)
    if not deleted:
        raise HTTPException(404, "Agent run not found.")
    return {"message": "Agent run deleted."}