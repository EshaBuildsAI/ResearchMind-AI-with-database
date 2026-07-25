"""
core/database.py
SQLAlchemy engine + session. Same code path works for SQLite (local dev,
zero setup) and PostgreSQL (production) — only DATABASE_URL changes.

Connection pooling (pool_size/max_overflow) matters once real concurrent
users hit the API — this is what stops "many users = DB connections
exhausted" from happening.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if is_sqlite:
    # Local dev fallback — no pooling concept, just needs the thread flag.
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # Postgres in production — pooling matters once real concurrent
    # users hit the API (this is what prevents "connections exhausted").
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — one DB session per request, always closed after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
