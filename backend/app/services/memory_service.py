"""
app/services/memory_service.py
Smart Memory — persistent per-document Q&A context that survives restarts.
V3 used a JSON file per doc_id; V4 uses a real DB table (SmartMemoryEntry)
scoped by user_id + document_id, so memory can't leak across users and
survives a server restart the same way the rest of the app's data does.
"""

from sqlalchemy.orm import Session

from app.models import SmartMemoryEntry

MAX_MEMORY_ENTRIES_PER_DOC = 20


def load_memory(db: Session, user_id: str, document_id: str) -> list:
    rows = (
        db.query(SmartMemoryEntry)
        .filter(SmartMemoryEntry.user_id == user_id, SmartMemoryEntry.document_id == document_id)
        .order_by(SmartMemoryEntry.created_at.asc())
        .all()
    )
    return [{"question": r.question, "answer": r.answer} for r in rows]


def save_memory_entry(db: Session, user_id: str, document_id: str, question: str, answer: str):
    entry = SmartMemoryEntry(user_id=user_id, document_id=document_id, question=question, answer=answer)
    db.add(entry)
    db.commit()

    # Trim to the most recent MAX_MEMORY_ENTRIES_PER_DOC entries for this doc.
    rows = (
        db.query(SmartMemoryEntry)
        .filter(SmartMemoryEntry.user_id == user_id, SmartMemoryEntry.document_id == document_id)
        .order_by(SmartMemoryEntry.created_at.desc())
        .offset(MAX_MEMORY_ENTRIES_PER_DOC)
        .all()
    )
    for row in rows:
        db.delete(row)
    db.commit()


def format_memory_for_prompt(db: Session, user_id: str, document_id: str, max_entries: int = 5) -> str:
    history = load_memory(db, user_id, document_id)[-max_entries:]
    if not history:
        return ""
    lines = ["Earlier questions asked about this document (for context):"]
    for entry in history:
        lines.append(f"- Q: {entry['question']}\n  A: {entry['answer'][:200]}")
    return "\n".join(lines)


def clear_memory(db: Session, user_id: str, document_id: str = None):
    q = db.query(SmartMemoryEntry).filter(SmartMemoryEntry.user_id == user_id)
    if document_id:
        q = q.filter(SmartMemoryEntry.document_id == document_id)
    q.delete()
    db.commit()
