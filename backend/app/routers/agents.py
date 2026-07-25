"""
app/routers/agents.py
Every agent endpoint returns the same AgentRunOut shape (steps + final
result) so the React side panel can render any agent with one component.

Document + topic-text are independent inputs on every agent except
Citation (which genuinely needs a document for page numbers): a request
needs at least ONE of them, and if a document is given but no topic text,
the topic is auto-extracted from the document. Multi-document context is
supported via `document_ids` (a list) on Research and Citation.

A `/agents/stream` endpoint + the WebSocket in routers/ws.py let the
frontend watch an agent run step-by-step in real time instead of waiting
for the whole thing to finish.
"""

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.models import AgentRun, Document, User
from app.schemas import AgentRequest, AgentRunOut, SummarizeReferenceRequest
from app.services import agent_service, guardrails, llm_service, rate_limit, usage_service, vectorstore
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


def _resolve_doc_ids(payload: AgentRequest) -> list:
    """document_ids (multi-document) takes priority; falls back to the
    single document_id for backward compatibility."""
    if payload.document_ids:
        return list(payload.document_ids)
    if payload.document_id:
        return [payload.document_id]
    return []


def _validate_documents(db: Session, user_id: str, doc_ids: list) -> list:
    docs = []
    for doc_id in doc_ids:
        docs.append(_validate_document(db, user_id, doc_id))
    return docs


def _resolve_question_or_topic(db: Session, user_id: str, payload: AgentRequest, require_document: bool = False) -> str:
    """Every agent (except Citation) accepts a document, a topic/question, or
    both. If a document is given but no text, the topic is auto-extracted
    from the first document. Raises 400 only if genuinely nothing usable
    was provided."""
    doc_ids = _resolve_doc_ids(payload)
    _validate_documents(db, user_id, doc_ids)
    if require_document and not doc_ids:
        raise HTTPException(400, "This agent needs a document — select one and try again.")

    question = (payload.question or "").strip()
    if question:
        is_valid, cleaned_or_error = guardrails.validate_question(question)
        if not is_valid:
            raise HTTPException(400, cleaned_or_error)
        guardrails.check_for_injection_attempt(cleaned_or_error)
        return cleaned_or_error

    if doc_ids:
        try:
            doc_text = vectorstore.get_full_document_text(user_id, doc_ids[0])
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
        "document_ids": run.document_ids(),
        "steps": [
            {
                "step_index": s.step_index, "name": s.name, "label": s.label,
                "status": s.status, "detail": json.loads(s.detail_json) if s.detail_json else None,
            }
            for s in run.steps
        ],
    }


def _enforce_agent_limits(db: Session, current_user: User):
    rate_limit.enforce("agent", current_user.id, settings.AGENT_RATE_LIMIT_PER_MINUTE)
    usage_service.enforce_daily_limit(db, current_user, "agent")


@router.post("/research", response_model=AgentRunOut)
def research_agent(payload: AgentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _enforce_agent_limits(db, current_user)
    question = _resolve_question_or_topic(db, current_user.id, payload)
    doc_ids = _resolve_doc_ids(payload)
    try:
        run = agent_service.run_research_agent(db, current_user.id, doc_ids or None, question)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    usage_service.increment_usage(db, current_user.id, "agent")
    return _serialize_run(run)


@router.post("/planner", response_model=AgentRunOut)
def planner_agent(payload: AgentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _enforce_agent_limits(db, current_user)
    question = _resolve_question_or_topic(db, current_user.id, payload)
    doc_ids = _resolve_doc_ids(payload)
    doc_id = doc_ids[0] if doc_ids else None
    try:
        topic = ""
        if doc_id:
            doc_text = vectorstore.get_full_document_text(current_user.id, doc_id)
            topic = llm_service.extract_topic(doc_text) if doc_text else ""
    except Exception:
        topic = ""
    try:
        run = agent_service.run_planner_agent(db, current_user.id, doc_id, question, topic=topic or question)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    usage_service.increment_usage(db, current_user.id, "agent")
    return _serialize_run(run)


@router.post("/recommendation", response_model=AgentRunOut)
def recommendation_agent(payload: AgentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _enforce_agent_limits(db, current_user)
    topic = _resolve_question_or_topic(db, current_user.id, payload)
    doc_ids = _resolve_doc_ids(payload)
    try:
        run = agent_service.run_recommendation_agent(db, current_user.id, doc_ids[0] if doc_ids else None, topic)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    usage_service.increment_usage(db, current_user.id, "agent")
    return _serialize_run(run)


@router.post("/timeline", response_model=AgentRunOut)
def timeline_agent(payload: AgentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _enforce_agent_limits(db, current_user)
    topic = _resolve_question_or_topic(db, current_user.id, payload)
    doc_ids = _resolve_doc_ids(payload)
    try:
        run = agent_service.run_timeline_agent(db, current_user.id, doc_ids[0] if doc_ids else None, topic)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    usage_service.increment_usage(db, current_user.id, "agent")
    return _serialize_run(run)


@router.post("/innovation", response_model=AgentRunOut)
def innovation_agent(payload: AgentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _enforce_agent_limits(db, current_user)
    topic = _resolve_question_or_topic(db, current_user.id, payload)
    doc_ids = _resolve_doc_ids(payload)
    doc_id = doc_ids[0] if doc_ids else None
    try:
        gaps = ""
        if doc_id:
            doc_text = vectorstore.get_full_document_text(current_user.id, doc_id)
            gaps = llm_service.detect_research_gaps(doc_text) if doc_text else ""
        run = agent_service.run_innovation_agent(db, current_user.id, doc_id, gaps, topic)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    usage_service.increment_usage(db, current_user.id, "agent")
    return _serialize_run(run)


@router.post("/citation", response_model=AgentRunOut)
def citation_agent(payload: AgentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _enforce_agent_limits(db, current_user)
    doc_ids = _resolve_doc_ids(payload)
    if not doc_ids:
        raise HTTPException(400, "The Citation Agent needs a document — it can't point to a page number without one.")
    _validate_documents(db, current_user.id, doc_ids)
    question = payload.question.strip()
    is_valid, cleaned_or_error = guardrails.validate_question(question)
    if not is_valid:
        raise HTTPException(400, cleaned_or_error)
    guardrails.check_for_injection_attempt(cleaned_or_error)
    try:
        run = agent_service.run_citation_agent(db, current_user.id, doc_ids, cleaned_or_error)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    usage_service.increment_usage(db, current_user.id, "agent")
    return _serialize_run(run)


@router.post("/summarize-reference", response_model=AgentRunOut)
def summarize_reference(
    payload: SummarizeReferenceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tool for the 'summarize this link' feature — any reference card any
    agent surfaced can be sent here to get fetched + summarized."""
    _enforce_agent_limits(db, current_user)
    if not payload.url or not payload.url.startswith(("http://", "https://")):
        raise HTTPException(400, "A valid http(s) URL is required.")
    try:
        run = agent_service.run_summarize_reference(
            db, current_user.id, payload.document_id, payload.url, payload.question or ""
        )
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    usage_service.increment_usage(db, current_user.id, "agent")
    return _serialize_run(run)


# ---------------- Streaming (WebSocket) trigger ----------------

_STREAMING_AGENT_TYPES = {"research", "planner", "recommendation", "timeline", "innovation", "citation"}


def _run_agent_in_background(agent_type: str, user_id: str, run_id: str, doc_ids: list, question: str, topic: str, gaps: str):
    """Runs in a background thread with its OWN db session (the request's
    session is closed by the time this executes) — same pattern as
    document background processing."""
    db = SessionLocal()
    try:
        run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            return
        doc_id = doc_ids[0] if doc_ids else None
        if agent_type == "research":
            agent_service.run_research_agent(db, user_id, doc_ids or None, question, run=run)
        elif agent_type == "planner":
            agent_service.run_planner_agent(db, user_id, doc_id, question, topic=topic or question, run=run)
        elif agent_type == "recommendation":
            agent_service.run_recommendation_agent(db, user_id, doc_id, topic or question, run=run)
        elif agent_type == "timeline":
            agent_service.run_timeline_agent(db, user_id, doc_id, topic or question, run=run)
        elif agent_type == "innovation":
            agent_service.run_innovation_agent(db, user_id, doc_id, gaps, topic or question, run=run)
        elif agent_type == "citation":
            agent_service.run_citation_agent(db, user_id, doc_ids, question, run=run)
    except Exception as e:
        agent_service.finish_run(db, run, status="failed", error=str(e))
    finally:
        db.close()


@router.post("/stream")
def start_streaming_agent(
    payload: AgentRequest,
    agent_type: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kicks off any agent in the background and returns immediately with a
    run_id + status='running'. Connect to ws://<host>/ws/agents/{run_id}?token=...
    to watch it complete step-by-step in real time (see routers/ws.py)."""
    if agent_type not in _STREAMING_AGENT_TYPES:
        raise HTTPException(400, f"Unknown or unsupported streaming agent_type: {agent_type}")

    _enforce_agent_limits(db, current_user)
    require_doc = agent_type == "citation"
    question = _resolve_question_or_topic(db, current_user.id, payload, require_document=require_doc)
    doc_ids = _resolve_doc_ids(payload)
    doc_id = doc_ids[0] if doc_ids else None

    topic, gaps = "", ""
    if agent_type in ("planner", "innovation") and doc_id:
        try:
            doc_text = vectorstore.get_full_document_text(current_user.id, doc_id)
            topic = llm_service.extract_topic(doc_text) if doc_text else ""
            if agent_type == "innovation":
                gaps = llm_service.detect_research_gaps(doc_text) if doc_text else ""
        except Exception:
            pass

    run = agent_service.start_run(db, current_user.id, doc_ids, agent_type, question)
    usage_service.increment_usage(db, current_user.id, "agent")
    background_tasks.add_task(
        _run_agent_in_background, agent_type, current_user.id, run.id, doc_ids, question, topic, gaps
    )
    return {"run_id": run.id, "status": "running"}


@router.get("/runs", response_model=list[AgentRunOut])
def list_runs(
    document_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    runs = agent_service.list_runs(db, current_user.id, document_id=document_id)
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
