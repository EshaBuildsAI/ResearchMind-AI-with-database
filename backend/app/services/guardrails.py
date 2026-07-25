"""
app/services/guardrails.py
Basic safety checks — pattern-level, not semantic. Documented honestly:
this catches obvious cases (empty/oversized input, common injection
phrasing, empty/junk AI output), not adversarial-input defense.
"""

import logging
import re

logger = logging.getLogger("researchmind")

MAX_QUESTION_LENGTH = 2000
MIN_QUESTION_LENGTH = 2

_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above) instructions",
    r"you are now (a|an) ",
    r"system prompt",
    r"act as (if )?you (have no|are not) restrictions",
    r"reveal your (instructions|system prompt|prompt)",
]
_INJECTION_REGEX = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def validate_question(question: str) -> tuple:
    if not question or not question.strip():
        return False, "Question cannot be empty."
    question = question.strip()
    if len(question) < MIN_QUESTION_LENGTH:
        return False, "Question is too short."
    if len(question) > MAX_QUESTION_LENGTH:
        return False, f"Question is too long (max {MAX_QUESTION_LENGTH} characters)."
    return True, question


def check_for_injection_attempt(text: str) -> bool:
    if not text:
        return False
    matched = bool(_INJECTION_REGEX.search(text))
    if matched:
        logger.warning(f"Possible prompt-injection pattern detected (first 100 chars): {text[:100]!r}")
    return matched


def validate_ai_output(output: str) -> tuple:
    if not output or not output.strip():
        return False, "The AI returned an empty response. Please try again."
    if len(output.strip()) < 3:
        return False, "The AI response was too short to be useful. Please try again."
    return True, output.strip()
