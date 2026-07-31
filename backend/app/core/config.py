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

    # Citation Agent's cross-encoder re-ranking (better confidence scores)
    # loads torch + sentence-transformers, which can push a free/hobby
    # hosting tier's ~1GB RAM limit into an out-of-memory crash. Off by
    # default; set to "true" once you're on a plan with more RAM. When
    # off, Citation Agent still works — it just uses the plain vector-
    # similarity confidence score instead of the re-ranked one.
    ENABLE_RERANKER = os.getenv("ENABLE_RERANKER", "false").lower() == "true"

    # ---------------- Export / memory dirs ----------------
    EXPORT_DIR = os.getenv("EXPORT_DIR", "exports")
    MEMORY_DIR = os.getenv("MEMORY_DIR", "memory")

    # ---------------- Rate limiting on paid endpoints ----------------
    CHAT_RATE_LIMIT_PER_MINUTE = int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "10"))
    AGENT_RATE_LIMIT_PER_MINUTE = int(os.getenv("AGENT_RATE_LIMIT_PER_MINUTE", "5"))

    # ---------------- Frontend URL (for email links) ----------------
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # ---------------- Email (Resend — HTTPS API, never blocked by hosting
    # platforms, unlike SMTP which Railway/Render often block outbound).
    # Free tier: 3,000 emails/month. Get a key at https://resend.com/api-keys
    # Falls back to SMTP (below) if this isn't set, then to console-logging
    # if neither is set — so local dev works with zero setup either way. ----------------
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")

    # ---------------- Email (SMTP — fallback if RESEND_API_KEY isn't set) ----------------
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@researchmind.ai")
    SMTP_FROM_NAME = "ResearchMind AI"

    # ---------------- Two-factor auth (TOTP — free, no SMS provider) ----------------
    TOTP_ISSUER = "ResearchMind AI"

    # ---------------- Admin bootstrap ----------------
    # Comma-separated usernames to auto-promote to admin on first login
    # after this env var is set — convenient for the very first admin account.
    ADMIN_USERNAMES = [u.strip() for u in os.getenv("ADMIN_USERNAMES", "").split(",") if u.strip()]

    # ---------------- Plan limits (free vs pro) — all enforced server-side ----------------
    FREE_PLAN_MAX_DOCUMENTS = int(os.getenv("FREE_PLAN_MAX_DOCUMENTS", "5"))
    FREE_PLAN_CHAT_PER_DAY = int(os.getenv("FREE_PLAN_CHAT_PER_DAY", "30"))
    FREE_PLAN_AGENT_PER_DAY = int(os.getenv("FREE_PLAN_AGENT_PER_DAY", "15"))
    PRO_PLAN_MAX_DOCUMENTS = int(os.getenv("PRO_PLAN_MAX_DOCUMENTS", "200"))
    PRO_PLAN_CHAT_PER_DAY = int(os.getenv("PRO_PLAN_CHAT_PER_DAY", "1000"))
    PRO_PLAN_AGENT_PER_DAY = int(os.getenv("PRO_PLAN_AGENT_PER_DAY", "500"))

    # ---------------- Stripe (test mode is entirely free — only real charges cost money) ----------------
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO", "")


settings = Settings()