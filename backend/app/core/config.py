"""
core/config.py
Central settings, loaded from environment variables (.env).
Nothing here is hardcoded so the same code runs in dev / staging / prod.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str, default: str = None) -> str:
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return val


class Settings:
    # ---------------- App ----------------
    APP_NAME = "ResearchMind AI"
    ENV = os.getenv("ENV", "development")  # development | production
    DEBUG = ENV == "development"

    # ---------------- Database ----------------
    # Postgres in prod, but SQLite fallback so the backend still boots
    # locally with zero setup while you wire Postgres up.
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///./researchmind.db",
    )

    # ---------------- Auth / JWT ----------------
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me-in-prod")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))  # access token
    JWT_REFRESH_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "7"))

    # ---------------- Rate limiting ----------------
    LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "10"))

    # ---------------- CORS ----------------
    FRONTEND_ORIGINS = os.getenv(
        "FRONTEND_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # ---------------- Uploads ----------------
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    SUPPORTED_FORMATS = ["pdf", "docx", "pptx", "xlsx", "txt"]

    # ---------------- AI provider (the only paid piece) ----------------
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    WHISPER_MODEL = "whisper-1"
    TTS_MODEL = "tts-1"
    TTS_VOICE = "alloy"

    # ---------------- Free research APIs ----------------
    ARXIV_API_URL = "http://export.arxiv.org/api/query"
    SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    OPENALEX_API_URL = "https://api.openalex.org/works"

    # ---------------- RAG / chunking ----------------
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 150
    TOP_K_RESULTS = 5
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # free, local, no API key
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "chroma_db")
    CHROMA_COLLECTION_NAME = "researchmind_documents"

    # ---------------- Export / memory dirs ----------------
    EXPORT_DIR = os.getenv("EXPORT_DIR", "exports")
    MEMORY_DIR = os.getenv("MEMORY_DIR", "memory")

    # ---------------- Rate limiting on paid endpoints ----------------
    CHAT_RATE_LIMIT_PER_MINUTE = int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "10"))
    AGENT_RATE_LIMIT_PER_MINUTE = int(os.getenv("AGENT_RATE_LIMIT_PER_MINUTE", "5"))


settings = Settings()
