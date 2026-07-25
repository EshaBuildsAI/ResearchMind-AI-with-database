"""
app/services/llm_service.py
The only paid call in the whole stack: GPT-4o-mini via the OpenAI API.
Everything else (embeddings, paper search) is free.
"""

import re

from openai import OpenAI

from app.core.config import settings
from app.services import prompts

_client = None


class LLMNotConfigured(Exception):
    """Raised when OPENAI_API_KEY isn't set — turned into a clean 503 by routers."""
    pass


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise LLMNotConfigured(
                "OPENAI_API_KEY is not set. Add it to your .env file to enable AI features."
            )
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def generate(prompt: str, max_tokens: int = 2048) -> str:
    """Send a prompt to GPT-4o-mini and return the plain text response."""
    client = _get_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


# ---------------- Feature entry points ----------------

def generate_summary(text: str, length: str = "medium") -> str:
    return generate(prompts.summary_prompt(text, length))


def answer_question(question: str, context_chunks: list) -> str:
    if not context_chunks:
        return "I couldn't find relevant content in this document to answer that."
    return generate(prompts.chat_prompt(question, context_chunks))


def answer_general_question(question: str) -> str:
    """Used when no document is attached — a normal AI-assistant-style answer
    from general knowledge, not restricted to any document context."""
    return generate(prompts.general_chat_prompt(question))


def generate_quiz(text: str, num_questions: int = 5) -> list:
    return _parse_quiz(generate(prompts.quiz_prompt(text, num_questions)))


def generate_flashcards(text: str, num_cards: int = 10) -> list:
    return _parse_flashcards(generate(prompts.flashcard_prompt(text, num_cards)))


def extract_topic(text: str) -> str:
    prompt = (
        "In 3 to 6 words, state the core research topic of the document below. "
        "Return ONLY the topic phrase, nothing else.\n\nDOCUMENT:\n"
        f"{text[:2000]}\n\nTOPIC:"
    )
    return generate(prompt).strip().strip('"')


def generate_proposal(text: str, degree_level: str = "BS", university: str = "") -> str:
    return generate(prompts.proposal_prompt(text, degree_level, university))


def generate_literature_review(text: str) -> str:
    return generate(prompts.literature_review_prompt(text))


def detect_research_gaps(text: str) -> str:
    return generate(prompts.research_gap_prompt(text))


def generate_presentation_outline(text: str, num_slides: int = 8) -> list:
    return _parse_presentation(generate(prompts.presentation_prompt(text, num_slides)))


def summarize_url_content(url: str, page_text: str, question: str = "") -> str:
    return generate(prompts.summarize_url_prompt(url, page_text, question))


# ---------------- Parsers (raw model text -> structured data) ----------------

def _parse_quiz(raw: str) -> list:
    questions = []
    blocks = re.split(r"\n(?=Q\d+:)", raw.strip())
    for block in blocks:
        q_match = re.search(r"Q\d+:\s*(.+)", block)
        options = dict(re.findall(r"([A-D])\)\s*(.+)", block))
        correct_match = re.search(r"Correct:\s*([A-D])", block)
        if q_match and options and correct_match:
            questions.append({
                "question": q_match.group(1).strip(),
                "options": options,
                "correct": correct_match.group(1).strip(),
            })
    return questions


def _parse_flashcards(raw: str) -> list:
    cards = []
    blocks = re.split(r"\n(?=Front:)", raw.strip())
    for block in blocks:
        front_match = re.search(r"Front:\s*(.+)", block)
        back_match = re.search(r"Back:\s*(.+)", block)
        if front_match and back_match:
            cards.append({"front": front_match.group(1).strip(), "back": back_match.group(1).strip()})
    return cards


def _parse_presentation(raw: str) -> list:
    slides = []
    blocks = re.split(r"\n(?=Slide\s*\d+:)", raw.strip())
    for block in blocks:
        title_match = re.search(r"Slide\s*\d+:\s*(.+)", block)
        bullets = re.findall(r"-\s*(.+)", block)
        if title_match:
            slides.append({"title": title_match.group(1).strip(), "bullets": [b.strip() for b in bullets]})
    return slides
