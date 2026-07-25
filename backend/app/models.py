"""
app/models.py
Database tables. Every piece of user data (documents, chat) carries a
user_id foreign key — this is what makes per-user isolation real instead
of a convention someone can forget to apply in a query.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Integer, Text, Boolean
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    username = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Login rate-limiting state (brute-force protection)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    documents = relationship(
        "Document", back_populates="owner", cascade="all, delete-orphan"
    )
    chat_messages = relationship(
        "ChatMessage", back_populates="owner", cascade="all, delete-orphan"
    )
    agent_runs = relationship(
        "AgentRun", cascade="all, delete-orphan"
    )
    smart_memory_entries = relationship(
        "SmartMemoryEntry", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    filename = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf | docx | pptx | xlsx | txt
    storage_path = Column(String(1000), nullable=False)  # local path or S3/R2 key
    status = Column(String(20), default="uploaded")  # uploaded | processing | ready | failed
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="documents")
    chat_messages = relationship(
        "ChatMessage", back_populates="document", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True, index=True)

    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    feature = Column(String(50), default="chat")  # chat | agent | quiz | flashcards | etc.

    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="chat_messages")
    document = relationship("Document", back_populates="chat_messages")


class AgentRun(Base):
    """One invocation of an agent (Research, Planner, Recommendation, Timeline,
    Innovation, Citation...). Drives the GUI's side panel: each run has ordered
    AgentStep rows the frontend renders as a step-tracker (retrieve -> search -> synthesize)."""
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True, index=True)

    agent_type = Column(String(50), nullable=False)  # research | planner | recommendation | timeline | innovation | citation
    question = Column(Text, nullable=False)
    status = Column(String(20), default="running")  # running | done | failed
    result_text = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)  # JSON-encoded structured result (sources, citations, etc.)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    steps = relationship("AgentStep", back_populates="run", cascade="all, delete-orphan",
                          order_by="AgentStep.step_index")


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id = Column(String, primary_key=True, default=gen_uuid)
    run_id = Column(String, ForeignKey("agent_runs.id"), nullable=False, index=True)
    step_index = Column(Integer, nullable=False)

    name = Column(String(100), nullable=False)       # e.g. "retrieve_docs", "search_web", "synthesize"
    label = Column(String(200), nullable=False)       # human-readable, e.g. "Searching arXiv + Semantic Scholar"
    status = Column(String(20), default="pending")    # pending | running | done | failed
    detail_json = Column(Text, nullable=True)         # JSON-encoded step output (paper cards, chunks, etc.)

    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("AgentRun", back_populates="steps")


class SmartMemoryEntry(Base):
    """Persistent per-document Q&A memory (the 'Smart Memory' feature) —
    a real DB table instead of the old per-doc JSON file, so it survives
    restarts and stays correctly scoped per user."""
    __tablename__ = "smart_memory"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)

    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
