"""app/services/prompts.py — centralized prompt templates for every AI feature."""


def topic_overview_prompt(topic: str) -> str:
    """Turns a bare topic into factual 'source material' — the output of
    this feeds into the SAME summary/quiz/flashcard/etc. prompts below as
    if it were document text, so every Tool works from a topic alone,
    not just an uploaded document."""
    return f"""Write a detailed, factual overview of the topic below, covering key
concepts, context, important facts, and any relevant history a student or
researcher would need. Be accurate and thorough (roughly 500-700 words).
Do not invent specific statistics or citations you're not confident about.

TOPIC:
{topic}

OVERVIEW:"""


def summary_prompt(text: str, length: str = "medium") -> str:
    length_map = {
        "short": "in 3-4 concise bullet points",
        "medium": "in 6-8 bullet points covering key findings, methods, and conclusions",
        "detailed": "as a detailed structured summary with sections: Overview, Methodology, "
                    "Key Findings, and Conclusion",
    }
    instruction = length_map.get(length, length_map["medium"])
    return f"""You are a research assistant. Summarize the following document {instruction}.
Be accurate and only use information present in the text. Do not invent facts.

DOCUMENT:
{text}

SUMMARY:"""


def general_chat_prompt(question: str) -> str:
    return f"""You are ResearchMind AI, a helpful research assistant. The user has not
attached a document to this question, so answer directly using your own general
knowledge — the way a normal AI assistant would. Be accurate and clear. Always answer
in the SAME language the question was asked in — if the question is in Urdu, answer in
Urdu; if in English, answer in English; and so on.

QUESTION:
{question}

ANSWER:"""


def chat_prompt(question: str, context_chunks: list) -> str:
    context = "\n\n".join(f"[Excerpt {i+1}]\n{chunk}" for i, chunk in enumerate(context_chunks))
    return f"""You are ResearchMind AI, a research assistant. Answer the user's question
using ONLY the context excerpts below. If the answer isn't in the context, say so honestly
instead of guessing. Always answer in the SAME language the question was asked in — if the
question is in Urdu, answer in Urdu; if in English, answer in English; and so on.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""


def quiz_prompt(text: str, num_questions: int = 5) -> str:
    return f"""Create {num_questions} multiple-choice quiz questions based on the document below.
For each question, provide 4 options (A-D) and clearly mark the correct answer.
Return the result in this exact format for each question:

Q1: <question text>
A) <option>
B) <option>
C) <option>
D) <option>
Correct: <letter>

DOCUMENT:
{text}

QUIZ:"""


def flashcard_prompt(text: str, num_cards: int = 10) -> str:
    return f"""Create {num_cards} flashcards from the document below.
Each flashcard should test one key concept, term, or fact.
Return the result in this exact format for each card:

Front: <term or question>
Back: <definition or answer>

DOCUMENT:
{text}

FLASHCARDS:"""


def literature_review_prompt(text: str) -> str:
    return f"""You are a research assistant writing a literature review section based on the
document below. Structure your response under these headings:

1. Introduction — what field/topic this work belongs to
2. Related Work — key themes, methods, and prior work discussed or referenced
3. Critical Analysis — strengths and weaknesses of the approach
4. Conclusion — how this document fits into the broader research landscape

Only use information present in the document. Do not invent citations.

DOCUMENT:
{text}

LITERATURE REVIEW:"""


def citation_answer_prompt(question: str, cited_chunks: list) -> str:
    context = "\n\n".join(
        f"[Source {i+1} — Page {c['page'] or 'N/A'}, confidence {c['confidence']}%]\n{c['text']}"
        for i, c in enumerate(cited_chunks)
    )
    return f"""You are a research assistant. Answer the question using ONLY the sources
below. After your answer, you do not need to repeat the citations — they will be
shown separately. If the sources don't contain the answer, say so honestly.
Always answer in the SAME language the question was asked in.

SOURCES:
{context}

QUESTION:
{question}

ANSWER:"""


def planner_intent_prompt(question: str) -> str:
    return f"""Classify the user's request into exactly ONE of these categories.
Return ONLY the category word, nothing else.

- recommendation: asking what to read/study next, related techniques or papers
- timeline: asking how a topic evolved over time, historical development
- innovation: asking for novel project ideas, research directions
- research_gap: asking what's missing, limitations, future work
- citation: asking for a specific fact with a page number / exact source
- general_chat: anything else — general questions about the document

USER REQUEST:
{question}

CATEGORY:"""


def proposal_prompt(text: str, degree_level: str, university: str) -> str:
    return f"""You are helping a student draft a {degree_level} final year research proposal,
based on the uploaded document below (which may be a related paper, prior work, or
background reading — not the proposal itself). Write an ORIGINAL proposal inspired by
this document's topic, not a summary of the document.

University: {university}

Structure the proposal with these exact sections:
1. Title
2. Introduction
3. Problem Statement
4. Objectives (3-5 bullet points)
5. Literature Review (brief, based on the document's topic)
6. Proposed Methodology
7. Expected Outcomes
8. Timeline (rough phase breakdown)

REFERENCE DOCUMENT:
{text}

PROPOSAL:"""


def recommendation_prompt(document_topic: str, related_papers: str) -> str:
    return f"""You are a research advisor. Based on the document's topic and the related
papers found below, recommend 4-6 techniques, methods, or papers the researcher should
look into next. For each recommendation, give a one-line reason tied to what's actually
in the related papers below. Do not invent papers that aren't listed.

DOCUMENT TOPIC:
{document_topic}

RELATED PAPERS FOUND:
{related_papers}

RECOMMENDATIONS (format: "- <name>: <one-line reason>"):"""


def timeline_prompt(topic: str, papers_by_year: str) -> str:
    return f"""You are a research historian. Using ONLY the papers listed below (with their
years), build a chronological timeline showing how this topic evolved. Group by year,
one line per key development. Do not invent papers or years not listed below.

TOPIC:
{topic}

PAPERS (year, title, snippet):
{papers_by_year}

TIMELINE (format: "YEAR — <development>: <paper title>"):"""


def innovation_prompt(research_gaps: str, related_papers: str) -> str:
    return f"""You are a research consultant. Using the research gaps identified below AND
the related/recent papers found online, generate 5 novel research project ideas.
Each idea should directly address one of the gaps or build on a trend visible in the
related papers. Rank them from most to least novel. Be specific — no generic ideas.

RESEARCH GAPS IDENTIFIED:
{research_gaps}

RELATED PAPERS (recent trends):
{related_papers}

NOVEL PROJECT IDEAS (format: "1. <idea title> — <2-3 sentence description tied to a gap or trend>"):"""


def research_gap_prompt(text: str) -> str:
    return f"""You are a research analyst. Carefully review the document below and identify:
1. Missing topics or areas not addressed
2. Explicitly stated future work
3. Dataset or sample limitations
4. Methodology gaps or weaknesses

Organize your answer under these four headings. Be specific and only base your
analysis on the document content.

DOCUMENT:
{text}

RESEARCH GAP ANALYSIS:"""


def presentation_prompt(text: str, num_slides: int = 8) -> str:
    return f"""Create an outline for a {num_slides}-slide presentation based on the document below.
For each slide, provide a title and 3-5 bullet points.
Return the result in this exact format for each slide:

Slide 1: <title>
- <bullet>
- <bullet>
- <bullet>

DOCUMENT:
{text}

PRESENTATION OUTLINE:"""


def summarize_url_prompt(url: str, page_text: str, question: str = "") -> str:
    """Used by the 'summarize this link' agent tool — fetched page content
    gets turned into a short cited summary, optionally focused on a question."""
    focus = f"\n\nFocus the summary on answering: {question}" if question else ""
    return f"""Summarize the web page below in 4-6 sentences. Be accurate, only use
information actually present in the text, and do not invent facts.{focus}

SOURCE URL: {url}

PAGE CONTENT:
{page_text[:6000]}

SUMMARY:"""