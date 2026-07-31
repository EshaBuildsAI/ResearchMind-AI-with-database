"""app/utils/text.py — shared helpers, no business logic."""

import os
import re


def get_file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def is_supported_file(filename: str, supported: list) -> bool:
    return get_file_extension(filename) in supported


def is_file_size_valid(file_bytes: bytes, max_mb: int) -> bool:
    return (len(file_bytes) / (1024 * 1024)) <= max_mb


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\S\r\n]{2,}", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list:
    text = clean_text(text)
    if not text:
        return []
    chunks = []
    start, text_len = 0, len(text)
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-_.]", "_", name)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def document_status_error(document) -> str:
    """Used by query/agents/features routers when a document isn't ready
    yet. Shows the real failure reason instead of the confusing
    'Document is still failed' message (found via real testing)."""
    if document.status == "failed":
        reason = document.error_message or "processing failed for an unknown reason"
        return f"This document failed to process: {reason}"
    return f"Document is still {document.status}. Try again once it's ready."


def truncate(text: str, max_chars: int = 300) -> str:
    return text if len(text) <= max_chars else text[:max_chars].rstrip() + "..."