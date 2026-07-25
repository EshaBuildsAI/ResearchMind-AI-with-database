"""
app/services/voice_service.py
Voice Research Assistant — speech-to-text (Whisper) and text-to-speech (TTS)
via the OpenAI API. Works via audio FILE upload (record on your device and
upload), not a live in-browser microphone stream.
"""

import io
import logging

from app.core.config import settings
from app.services.llm_service import _get_client

logger = logging.getLogger("researchmind")


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    client = _get_client()
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename
    try:
        transcript = client.audio.transcriptions.create(model=settings.WHISPER_MODEL, file=audio_file)
        return transcript.text.strip()
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        raise


def generate_speech(text: str) -> bytes:
    """Returns MP3 bytes. Input capped at 4000 characters (API limit)."""
    client = _get_client()
    try:
        response = client.audio.speech.create(
            model=settings.TTS_MODEL, voice=settings.TTS_VOICE, input=text[:4000],
        )
        return response.content
    except Exception as e:
        logger.error(f"Speech generation failed: {e}")
        raise
