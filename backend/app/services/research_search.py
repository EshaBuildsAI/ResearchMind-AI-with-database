"""
app/services/research_search.py
Tool functions the agents call: arXiv + Semantic Scholar + OpenAlex paper
search (all free), and a URL fetch-and-summarize tool ("summarize this link").

Semantic Scholar is used directly wherever paper search happens (not as an
optional fallback) — the dedicated API key from settings.SEMANTIC_SCHOLAR_API_KEY
is always attached so requests use the user's own rate limit.
"""

import logging
import re
import time
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from app.services import llm_service

logger = logging.getLogger("researchmind")


def _sanitize_search_query(query: str, max_words: int = 12) -> str:
    """Both Semantic Scholar and OpenAlex treat ?/* as wildcards, not literal
    punctuation — strip anything that isn't a letter/number/space/hyphen, and
    trim to the first N words (keyword phrases match far better than sentences)."""
    cleaned = re.sub(r"[^\w\s-]", " ", query)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    words = cleaned.split()
    if len(words) > max_words:
        cleaned = " ".join(words[:max_words])
    return cleaned


def _semantic_scholar_headers() -> dict:
    headers = {"User-Agent": "ResearchMindAI/1.0 (research assistant)"}
    if settings.SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY
    return headers


def search_arxiv(query: str, max_results: int = 3) -> list:
    """Free, no API key required. Always runs alongside Semantic Scholar."""
    query = _sanitize_search_query(query)
    try:
        params = {"search_query": f"all:{query}", "max_results": max_results}
        response = requests.get(settings.ARXIV_API_URL, params=params, timeout=10)
        root = ET.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        results = []
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns).text.strip()
            link = entry.find("atom:id", ns).text.strip()
            summary = entry.find("atom:summary", ns).text.strip()
            results.append({"title": title, "url": link, "snippet": summary[:300], "source": "arXiv"})
        return results
    except Exception as e:
        logger.warning(f"[arXiv] search failed: {e}")
        return []


def search_semantic_scholar(query: str, max_results: int = 5, _retrying: bool = False) -> list:
    """Primary paper-search tool — always attaches the dedicated API key."""
    query = _sanitize_search_query(query)
    try:
        params = {"query": query, "limit": max_results, "fields": "title,abstract,url,year"}
        headers = _semantic_scholar_headers()
        response = requests.get(settings.SEMANTIC_SCHOLAR_API_URL, params=params, headers=headers, timeout=15)

        if response.status_code == 429:
            logger.warning("[Semantic Scholar] rate limited (429)")
            if not _retrying:
                time.sleep(3)
                return search_semantic_scholar(query, max_results, _retrying=True)
            return []
        if response.status_code != 200:
            logger.warning(f"[Semantic Scholar] non-200: {response.status_code} — {response.text[:200]}")
            return []

        data = response.json()
        results = []
        for paper in data.get("data", []):
            results.append({
                "title": paper.get("title", "Untitled"),
                "url": paper.get("url", ""),
                "snippet": (paper.get("abstract") or "")[:300],
                "source": "Semantic Scholar",
                "year": paper.get("year"),
            })
        return results
    except requests.exceptions.Timeout:
        logger.warning("[Semantic Scholar] request timed out")
        return []
    except Exception as e:
        logger.warning(f"[Semantic Scholar] search failed: {e}")
        return []


def _openalex_abstract(work: dict) -> str:
    inverted = work.get("abstract_inverted_index")
    if not inverted:
        return ""
    positions = {}
    for word, idxs in inverted.items():
        for idx in idxs:
            positions[idx] = word
    return " ".join(positions[i] for i in sorted(positions))


def search_openalex(query: str, max_results: int = 5) -> list:
    """Free fallback with a much more generous rate limit than Semantic
    Scholar's shared tier — used only when Semantic Scholar returns nothing."""
    query = _sanitize_search_query(query)
    try:
        params = {"search": query, "per-page": max_results}
        headers = {"User-Agent": "ResearchMindAI/1.0 (research assistant; mailto:researchmindai@example.com)"}
        response = requests.get(settings.OPENALEX_API_URL, params=params, headers=headers, timeout=15)
        if response.status_code != 200:
            logger.warning(f"[OpenAlex] non-200: {response.status_code}")
            return []
        data = response.json()
        results = []
        for work in data.get("results", []):
            results.append({
                "title": work.get("title") or "Untitled",
                "url": work.get("id", ""),
                "snippet": _openalex_abstract(work)[:300],
                "source": "OpenAlex",
                "year": work.get("publication_year"),
            })
        return results
    except Exception as e:
        logger.warning(f"[OpenAlex] search failed: {e}")
        return []


def search_related_papers(query: str, max_results: int = 5) -> list:
    """Semantic Scholar first (the primary, key-backed source); OpenAlex only
    steps in if Semantic Scholar genuinely returns nothing."""
    results = search_semantic_scholar(query, max_results)
    if results:
        return results
    logger.info("[Fallback] Semantic Scholar returned nothing — trying OpenAlex.")
    return search_openalex(query, max_results)


# ---------------- URL fetch-and-summarize tool ("summarize this link") ----------------

def fetch_url_text(url: str, max_chars: int = 15000) -> str:
    """Fetch a web page and extract readable text (used when the user asks
    an agent to summarize a specific reference/link it surfaced)."""
    headers = {"User-Agent": "Mozilla/5.0 (ResearchMindAI/1.0 research assistant)"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and "xml" not in content_type:
        # e.g. a raw PDF link — not handled here, tell the caller honestly
        raise ValueError("This link isn't a readable web page (not HTML) — can't extract text from it.")

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()
    return text[:max_chars]


def summarize_url(url: str, question: str = "") -> dict:
    """Full tool: fetch a URL, then ask GPT-4o-mini for a short cited summary.
    Returns {"url": str, "summary": str}. Raises on fetch failure — caller
    turns that into a clean error message rather than a silent empty result."""
    page_text = fetch_url_text(url)
    if not page_text:
        raise ValueError("Couldn't extract any readable text from that page.")
    summary = llm_service.summarize_url_content(url, page_text, question)
    return {"url": url, "summary": summary}
