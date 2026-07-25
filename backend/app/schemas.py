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

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class MessageResponse(BaseModel):
    message: str


class RefreshRequest(BaseModel):
    refresh_token: str


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


# ---------------- AI Features ----------------

class SummaryRequest(BaseModel):
    document_id: str
    length: str = "medium"  # short | medium | detailed


class QuizRequest(BaseModel):
    document_id: str
    num_questions: int = 5


class FlashcardRequest(BaseModel):
    document_id: str
    num_cards: int = 10


class ProposalRequest(BaseModel):
    document_id: str
    degree_level: str = "BS"
    university: str = ""


class PresentationRequest(BaseModel):
    document_id: str
    num_slides: int = 8


class SmartMemoryOut(BaseModel):
    question: str
    answer: str


# ---------------- Voice ----------------

class TTSRequest(BaseModel):
    text: str