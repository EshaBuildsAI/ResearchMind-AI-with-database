"""
app/schemas.py
Pydantic models = automatic input validation. Garbage/malicious input gets
rejected with a clean 422 before it ever touches business logic.
"""

import re
from pydantic import BaseModel, EmailStr, field_validator

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,20}$")


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        if not USERNAME_REGEX.match(v):
            raise ValueError(
                "Username must be 3-20 characters: letters, numbers, underscores only."
            )
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v


class LoginRequest(BaseModel):
    identifier: str  # username OR email
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    email_verified: bool = False
    is_admin: bool = False
    plan: str = "free"
    totp_enabled: bool = False

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginResultResponse(BaseModel):
    """Returned by /auth/login. If the account has 2FA enabled, tokens are
    withheld and a short-lived pending_token is returned instead — the
    frontend must call /auth/login/2fa with it + a TOTP code to finish."""
    requires_2fa: bool = False
    pending_token: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: UserOut | None = None


class MessageResponse(BaseModel):
    message: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------- Email verification / password reset ----------------

class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_valid(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v


# ---------------- Two-factor authentication ----------------

class Enable2FAResponse(BaseModel):
    secret: str
    qr_code_base64: str


class Confirm2FARequest(BaseModel):
    code: str


class Login2FARequest(BaseModel):
    pending_token: str
    code: str


class Disable2FARequest(BaseModel):
    code: str


# ---------------- Documents ----------------

class DocumentOut(BaseModel):
    id: str
    filename: str
    file_type: str
    status: str
    chunk_count: int
    error_message: str | None = None
    created_at: str

    class Config:
        from_attributes = True


# ---------------- Chat / Query ----------------

class ChatRequest(BaseModel):
    question: str
    document_id: str | None = None
    document_ids: list[str] | None = None  # multi-document context; if set, takes priority over document_id


class SourceChunk(BaseModel):
    text: str
    page: int | None = None
    confidence: float | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list = []


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    feature: str
    created_at: str

    class Config:
        from_attributes = True


# ---------------- Agents ----------------

class AgentRequest(BaseModel):
    question: str = ""
    document_id: str | None = None
    document_ids: list[str] | None = None  # multi-document context; if set, takes priority over document_id


class SummarizeReferenceRequest(BaseModel):
    url: str
    question: str | None = ""
    document_id: str | None = None


class AgentStepOut(BaseModel):
    step_index: int
    name: str
    label: str
    status: str
    detail: dict | list | None = None


class AgentRunOut(BaseModel):
    id: str
    agent_type: str
    question: str
    status: str
    result_text: str | None = None
    result: dict | list | None = None
    error_message: str | None = None
    steps: list[AgentStepOut] = []
    created_at: str
    document_ids: list[str] = []


# ---------------- AI Features ----------------

class SummaryRequest(BaseModel):
    document_id: str | None = None
    topic: str | None = None
    length: str = "medium"  # short | medium | detailed


class QuizRequest(BaseModel):
    document_id: str | None = None
    topic: str | None = None
    num_questions: int = 5


class FlashcardRequest(BaseModel):
    document_id: str | None = None
    topic: str | None = None
    num_cards: int = 10


class ProposalRequest(BaseModel):
    document_id: str | None = None
    topic: str | None = None
    degree_level: str = "BS"
    university: str = ""


class PresentationRequest(BaseModel):
    document_id: str | None = None
    topic: str | None = None
    num_slides: int = 8


class SmartMemoryOut(BaseModel):
    question: str
    answer: str


# ---------------- Voice ----------------

class TTSRequest(BaseModel):
    text: str


# ---------------- Usage / plan ----------------

class UsageBucketOut(BaseModel):
    used: int
    limit: int | None = None


class UsageSummaryOut(BaseModel):
    plan: str
    documents: UsageBucketOut
    chat_today: UsageBucketOut
    agent_today: UsageBucketOut


# ---------------- Billing (Stripe) ----------------

class CheckoutSessionOut(BaseModel):
    checkout_url: str


class BillingPortalOut(BaseModel):
    portal_url: str


# ---------------- Admin ----------------

class AdminUserOut(BaseModel):
    id: str
    username: str
    email: str
    plan: str
    is_admin: bool
    email_verified: bool
    document_count: int
    created_at: str


class AdminStatsOut(BaseModel):
    total_users: int
    total_documents: int
    total_chat_messages: int
    total_agent_runs: int
    users_by_plan: dict
    agent_runs_by_type: dict
    feature_usage: dict
    signups_last_7_days: dict