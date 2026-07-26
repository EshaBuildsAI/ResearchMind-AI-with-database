"""
app/routers/voice.py
Voice Assistant — upload a voice question (audio file), get it transcribed,
answered via RAG, and optionally returned as spoken audio (TTS).
"""

import io

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import ChatMessage, User
from app.schemas import TTSRequest
from app.services import guardrails, llm_service, rate_limit, vectorstore, voice_service
from app.services.llm_service import LLMNotConfigured

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/ask")
async def voice_ask(
    audio: UploadFile = File(...),
    document_id: str | None = Form(None),
    speak_response: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rate_limit.enforce("chat", current_user.id, settings.CHAT_RATE_LIMIT_PER_MINUTE)
    audio_bytes = await audio.read()

    try:
        question = voice_service.transcribe_audio(audio_bytes, audio.filename or "audio.wav")
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    except Exception:
        raise HTTPException(422, "Couldn't transcribe that audio. Try a clearer recording (wav/mp3/m4a).")

    is_valid, cleaned_or_error = guardrails.validate_question(question)
    if not is_valid:
        raise HTTPException(400, f"Transcribed question was invalid: {cleaned_or_error}")
    question = cleaned_or_error

    if document_id:
        chunks = vectorstore.query(current_user.id, question, doc_id=document_id)
        try:
            answer = llm_service.answer_question(question, chunks)
        except LLMNotConfigured as e:
            raise HTTPException(503, str(e))
    else:
        try:
            answer = llm_service.answer_general_question(question)
        except LLMNotConfigured as e:
            raise HTTPException(503, str(e))

    db.add(ChatMessage(user_id=current_user.id, document_id=document_id, role="user",
                        content=question, feature="voice"))
    db.add(ChatMessage(user_id=current_user.id, document_id=document_id, role="assistant",
                        content=answer, feature="voice"))
    db.commit()

    response = {"question": question, "answer": answer}

    if speak_response:
        try:
            audio_out = voice_service.generate_speech(answer)
            import base64
            response["audio_base64"] = base64.b64encode(audio_out).decode("utf-8")
        except Exception:
            response["audio_base64"] = None
            response["voice_note"] = "Answer generated, but speech synthesis failed."

    return response


@router.post("/speak")
def speak(payload: TTSRequest, current_user: User = Depends(get_current_user)):
    """Standalone text-to-speech — returns an MP3 stream."""
    try:
        audio_bytes = voice_service.generate_speech(payload.text)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
    except Exception:
        raise HTTPException(502, "Speech generation failed. Please try again.")
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
