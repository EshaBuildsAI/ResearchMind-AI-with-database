"""
app/services/agent_service.py
Multi-step agent pipelines built with LangGraph — real tool-calling
orchestration (each step is an inspectable graph node), not a single prompt
pretending to be an agent.

Every run is persisted as an AgentRun + ordered AgentStep rows so the React
side panel can render a live step-tracker (retrieve -> search -> synthesize)
and reopen past runs later. Each step is also broadcast in real time over
broadcaster.py so a connected WebSocket sees updates as they happen,
instead of waiting for the whole run to finish.
"""

import json
from typing import TypedDict, List

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.models import AgentRun, AgentStep
from app.services import llm_service, memory_service, research_search, vectorstore, broadcaster, reranker_service
from app.services.prompts import (
    recommendation_prompt, timeline_prompt, innovation_prompt,
    citation_answer_prompt, planner_intent_prompt,
)


def _doc_ids_json(doc_ids) -> str | None:
    if not doc_ids:
        return None
    if isinstance(doc_ids, str):
        doc_ids = [doc_ids]
    return json.dumps(list(doc_ids))


def _first_doc_id(doc_ids):
    if not doc_ids:
        return None
    if isinstance(doc_ids, str):
        return doc_ids
    return doc_ids[0] if doc_ids else None


# ---------------- Run/step persistence helpers (drive the GUI panel + WS stream) ----------------

def start_run(db: Session, user_id: str, doc_ids, agent_type: str, question: str) -> AgentRun:
    run = AgentRun(
        user_id=user_id, document_id=_first_doc_id(doc_ids), document_ids_json=_doc_ids_json(doc_ids),
        agent_type=agent_type, question=question, status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    broadcaster.publish(run.id, {"type": "run_started", "run_id": run.id, "agent_type": agent_type})
    return run


def add_step(db: Session, run: AgentRun, index: int, name: str, label: str,
             status: str = "done", detail: dict = None) -> AgentStep:
    step = AgentStep(
        run_id=run.id, step_index=index, name=name, label=label, status=status,
        detail_json=json.dumps(detail) if detail is not None else None,
    )
    db.add(step)
    db.commit()
    broadcaster.publish(run.id, {
        "type": "step", "run_id": run.id, "step_index": index, "name": name,
        "label": label, "status": status, "detail": detail,
    })
    return step


def finish_run(db: Session, run: AgentRun, result_text: str = None, result_json: dict = None,
                status: str = "done", error: str = None):
    run.status = status
    run.result_text = result_text
    run.result_json = json.dumps(result_json) if result_json is not None else None
    run.error_message = error
    db.commit()
    db.refresh(run)
    broadcaster.publish(run.id, {
        "type": "run_finished", "run_id": run.id, "status": status,
        "result_text": result_text, "result": result_json, "error": error,
    })
    return run


def delete_run(db: Session, user_id: str, run_id: str) -> bool:
    run = db.query(AgentRun).filter(AgentRun.id == run_id, AgentRun.user_id == user_id).first()
    if not run:
        return False
    db.delete(run)
    db.commit()
    return True


def list_runs(db: Session, user_id: str, document_id: str = None, limit: int = 50) -> list:
    q = db.query(AgentRun).filter(AgentRun.user_id == user_id)
    if document_id:
        q = q.filter(AgentRun.document_id == document_id)
    return q.order_by(AgentRun.created_at.desc()).limit(limit).all()


# =====================================================================
# RESEARCH AGENT — retrieve_docs -> search_web -> synthesize
# (supports zero, one, or multiple documents as context)
# =====================================================================

class AgentState(TypedDict):
    question: str
    doc_ids: list
    user_id: str
    doc_context: List[str]
    web_results: List[dict]
    answer: str


def _build_research_graph(user_id: str, doc_ids: list | None):
    def node_retrieve(state: AgentState) -> AgentState:
        if doc_ids:
            state["doc_context"] = vectorstore.query(user_id, state["question"], doc_id=doc_ids)
        else:
            state["doc_context"] = []
        return state

    def node_search(state: AgentState) -> AgentState:
        state["web_results"] = (
            research_search.search_arxiv(state["question"])
            + research_search.search_related_papers(state["question"])
        )
        return state

    def node_synthesize(state: AgentState) -> AgentState:
        doc_context = "\n\n".join(state["doc_context"]) or "No document was provided, or no relevant passage was found."
        web_context = "\n\n".join(
            f"[{r['source']}] {r['title']} ({r['url']}): {r['snippet']}" for r in state["web_results"]
        ) or "No related papers found online."
        prompt = f"""You are a Research Assistant Agent. Write a substantive, direct answer to the
question below, using the document context (if any) and the related papers as your source
material. Explain the actual research findings and reasoning in your own words — do NOT just
list or dump links. Only mention a source by name inline where it genuinely supports a claim
(e.g. "the document explains..." or "recent work on this, such as [arXiv] Paper Title, shows...").
End your answer with a short "Further reading" section listing the source titles and links, so
the reader can go deeper — but that list comes LAST, after the real explanation, never before it.
Only use information actually present below — do not invent facts or citations. Always answer
in the SAME language the question was asked in.

DOCUMENT CONTEXT:
{doc_context}

RELATED PAPERS:
{web_context}

QUESTION:
{state['question']}

ANSWER (explanation first, "Further reading" links at the very end):"""
        state["answer"] = llm_service.generate(prompt)
        return state

    graph = StateGraph(AgentState)
    graph.add_node("retrieve_docs", node_retrieve)
    graph.add_node("search_web", node_search)
    graph.add_node("synthesize", node_synthesize)
    graph.set_entry_point("retrieve_docs")
    graph.add_edge("retrieve_docs", "search_web")
    graph.add_edge("search_web", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


def run_research_agent(db: Session, user_id: str, doc_ids, question: str, run: AgentRun = None) -> AgentRun:
    """doc_ids: None, a single doc_id string, or a list of doc_ids (multi-document context).
    Pass an existing `run` (from start_run) to reuse it — used by the streaming/background path."""
    doc_id_list = [doc_ids] if isinstance(doc_ids, str) else (list(doc_ids) if doc_ids else [])
    run = run or start_run(db, user_id, doc_id_list, "research", question)
    try:
        agent = _build_research_graph(user_id, doc_id_list or None)
        result = agent.invoke({
            "question": question, "doc_ids": doc_id_list, "user_id": user_id,
            "doc_context": [], "web_results": [], "answer": "",
        })

        retrieve_label = (
            f"Retrieving relevant passages from {len(doc_id_list)} document(s)" if doc_id_list
            else "No document provided — skipping document retrieval"
        )
        add_step(db, run, 0, "retrieve_docs", retrieve_label, detail={"chunks_found": len(result["doc_context"])})
        add_step(db, run, 1, "search_web", "Searching arXiv + Semantic Scholar",
                 detail={"papers": result["web_results"]})
        add_step(db, run, 2, "synthesize", "Synthesizing a cited answer",
                 detail={"answer_preview": result["answer"][:200]})

        if doc_id_list:
            memory_service.save_memory_entry(db, user_id, doc_id_list[0], question, result["answer"])
        return finish_run(db, run, result_text=result["answer"], result_json={"sources": result["web_results"]})
    except Exception as e:
        return finish_run(db, run, status="failed", error=str(e))


def quick_research_answer(user_id: str, doc_id: str | None, question: str) -> str:
    """Lightweight version of the Research Agent for contexts that just need
    an answer string — no AgentRun/step persistence, no GUI panel. Used by
    the Voice Assistant's 'research mode' so a spoken question can get the
    same doc+web-search-backed answer as the text Research Agent, not just
    whatever GPT already knows."""
    doc_id_list = [doc_id] if doc_id else []
    agent = _build_research_graph(user_id, doc_id_list or None)
    result = agent.invoke({
        "question": question, "doc_ids": doc_id_list, "user_id": user_id,
        "doc_context": [], "web_results": [], "answer": "",
    })
    return result["answer"]


# =====================================================================
# ADDITIONAL AGENTS — each does a real Semantic Scholar tool call
# before asking GPT-4o-mini to synthesize.
# =====================================================================

def run_recommendation_agent(db: Session, user_id: str, doc_id, topic_query: str, run: AgentRun = None) -> AgentRun:
    run = run or start_run(db, user_id, doc_id, "recommendation", topic_query)
    try:
        papers = research_search.search_related_papers(topic_query, max_results=6)
        add_step(db, run, 0, "search_web", "Searching Semantic Scholar for related papers",
                 detail={"papers": papers})

        if not papers:
            return finish_run(db, run, result_text=(
                "No related papers could be found online right now, so no "
                "recommendations could be generated."
            ), result_json={"sources": []})

        papers_text = "\n\n".join(f"- {p['title']} ({p.get('year')}): {p['snippet']}" for p in papers)
        recommendations = llm_service.generate(recommendation_prompt(topic_query, papers_text))
        add_step(db, run, 1, "synthesize", "Ranking recommendations from the results",
                 detail={"preview": recommendations[:200]})
        return finish_run(db, run, result_text=recommendations, result_json={"sources": papers})
    except Exception as e:
        return finish_run(db, run, status="failed", error=str(e))


def run_timeline_agent(db: Session, user_id: str, doc_id, topic_query: str, run: AgentRun = None) -> AgentRun:
    run = run or start_run(db, user_id, doc_id, "timeline", topic_query)
    try:
        papers = research_search.search_related_papers(topic_query, max_results=8)
        papers = [p for p in papers if p.get("year")]
        papers.sort(key=lambda p: p["year"])
        add_step(db, run, 0, "search_web", "Searching Semantic Scholar, sorted by year",
                 detail={"papers": papers})

        if not papers:
            return finish_run(db, run, result_text=(
                "No dated papers could be found online right now, so a timeline "
                "could not be built."
            ), result_json={"sources": []})

        papers_text = "\n".join(f"{p['year']} — {p['title']}: {p['snippet']}" for p in papers)
        timeline = llm_service.generate(timeline_prompt(topic_query, papers_text))
        add_step(db, run, 1, "synthesize", "Building the chronological timeline",
                 detail={"preview": timeline[:200]})
        return finish_run(db, run, result_text=timeline, result_json={"sources": papers})
    except Exception as e:
        return finish_run(db, run, status="failed", error=str(e))


def run_innovation_agent(db: Session, user_id: str, doc_id, research_gaps_text: str, topic_query: str, run: AgentRun = None) -> AgentRun:
    run = run or start_run(db, user_id, doc_id, "innovation", topic_query)
    try:
        papers = research_search.search_related_papers(topic_query, max_results=6)
        add_step(db, run, 0, "search_web", "Searching Semantic Scholar for recent trends",
                 detail={"papers": papers})
        papers_text = "\n\n".join(f"- {p['title']} ({p.get('year')}): {p['snippet']}" for p in papers) \
            or "No related papers found online."

        ideas = llm_service.generate(innovation_prompt(research_gaps_text, papers_text))
        add_step(db, run, 1, "synthesize", "Generating novel project ideas",
                 detail={"preview": ideas[:200]})
        return finish_run(db, run, result_text=ideas, result_json={"sources": papers})
    except Exception as e:
        return finish_run(db, run, status="failed", error=str(e))


def run_citation_agent(db: Session, user_id: str, doc_ids, question: str, run: AgentRun = None) -> AgentRun:
    """doc_ids: a single doc_id string or a list of doc_ids (multi-document
    citations — each citation card is labeled with which document it came from).
    Pass an existing `run` to reuse it — used by the streaming/background path."""
    doc_id_list = [doc_ids] if isinstance(doc_ids, str) else list(doc_ids)
    run = run or start_run(db, user_id, doc_id_list, "citation", question)
    try:
        cited_chunks = vectorstore.query_with_metadata(user_id, question, doc_id=doc_id_list)
        # Re-rank with a free local cross-encoder for a more accurate,
        # calibrated confidence score than raw vector-similarity distance.
        cited_chunks = reranker_service.rerank(question, cited_chunks)
        add_step(db, run, 0, "retrieve_docs", "Retrieving page-level citations (re-ranked for accuracy)",
                 detail={"citations": cited_chunks})

        if not cited_chunks:
            return finish_run(db, run, result_text=(
                "No relevant passages were found in this document for that question."
            ), result_json={"citations": []})

        answer = llm_service.generate(citation_answer_prompt(question, cited_chunks))
        add_step(db, run, 1, "synthesize", "Writing the cited answer", detail={"preview": answer[:200]})
        return finish_run(db, run, result_text=answer, result_json={"citations": cited_chunks})
    except Exception as e:
        return finish_run(db, run, status="failed", error=str(e))


def run_summarize_reference(db: Session, user_id: str, doc_id: str, url: str, question: str = "") -> AgentRun:
    """The 'summarize this link' tool — any agent's reference card can trigger this."""
    run = start_run(db, user_id, doc_id, "summarize_reference", url)
    try:
        add_step(db, run, 0, "fetch_url", f"Fetching {url}")
        result = research_search.summarize_url(url, question)
        add_step(db, run, 1, "synthesize", "Summarizing the page content",
                 detail={"preview": result["summary"][:200]})
        return finish_run(db, run, result_text=result["summary"], result_json={"url": url})
    except Exception as e:
        return finish_run(db, run, status="failed", error=str(e))


# =====================================================================
# PLANNER AGENT — real conditional routing (LangGraph decides the path)
# =====================================================================

class PlannerState(TypedDict):
    question: str
    doc_id: str
    user_id: str
    topic: str
    research_gaps: str
    intent: str
    result: dict


def _node_classify_intent(state: PlannerState) -> PlannerState:
    intent = llm_service.generate(planner_intent_prompt(state["question"])).strip().lower()
    valid = {"recommendation", "timeline", "innovation", "research_gap", "citation", "general_chat"}
    state["intent"] = intent if intent in valid else "general_chat"
    return state


def _route_by_intent(state: PlannerState) -> str:
    return state["intent"]


def _build_planner_graph():
    def node_recommendation(state):
        papers = research_search.search_related_papers(state["topic"] or state["question"], max_results=6)
        papers_text = "\n\n".join(f"- {p['title']} ({p.get('year')}): {p['snippet']}" for p in papers)
        state["result"] = {
            "recommendations": llm_service.generate(recommendation_prompt(state["topic"], papers_text)),
            "sources": papers,
        }
        return state

    def node_timeline(state):
        papers = research_search.search_related_papers(state["topic"] or state["question"], max_results=8)
        papers = sorted([p for p in papers if p.get("year")], key=lambda p: p["year"])
        papers_text = "\n".join(f"{p['year']} — {p['title']}: {p['snippet']}" for p in papers)
        state["result"] = {
            "timeline": llm_service.generate(timeline_prompt(state["topic"], papers_text)) if papers else
            "No dated papers found online.",
            "sources": papers,
        }
        return state

    def node_innovation(state):
        papers = research_search.search_related_papers(state["topic"] or state["question"], max_results=6)
        papers_text = "\n\n".join(f"- {p['title']} ({p.get('year')}): {p['snippet']}" for p in papers)
        state["result"] = {
            "ideas": llm_service.generate(innovation_prompt(state["research_gaps"], papers_text)),
            "sources": papers,
        }
        return state

    def node_research_gap(state):
        if not state["doc_id"]:
            state["result"] = {"gaps": "Research Gap analysis needs an uploaded document — please select one and try again."}
            return state
        doc_text = vectorstore.get_full_document_text(state["user_id"], state["doc_id"])
        state["result"] = {"gaps": llm_service.detect_research_gaps(doc_text)}
        return state

    def node_citation(state):
        if not state["doc_id"]:
            state["result"] = {"answer": "The Citation Agent needs an uploaded document to point to a page number — please select one and try again.", "citations": []}
            return state
        cited_chunks = vectorstore.query_with_metadata(state["user_id"], state["question"], doc_id=state["doc_id"])
        cited_chunks = reranker_service.rerank(state["question"], cited_chunks)
        answer = llm_service.generate(citation_answer_prompt(state["question"], cited_chunks)) if cited_chunks else \
            "No relevant passages were found in this document."
        state["result"] = {"answer": answer, "citations": cited_chunks}
        return state

    def node_general_chat(state):
        if state["doc_id"]:
            chunks = vectorstore.query(state["user_id"], state["question"], doc_id=state["doc_id"])
            state["result"] = {"answer": llm_service.answer_question(state["question"], chunks)}
        else:
            # No document attached — same fallback as the standalone Chat
            # tool: answer from general knowledge instead of the
            # document-restricted "couldn't find relevant content" message.
            state["result"] = {"answer": llm_service.answer_general_question(state["question"])}
        return state

    graph = StateGraph(PlannerState)
    graph.add_node("classify_intent", _node_classify_intent)
    graph.add_node("recommendation", node_recommendation)
    graph.add_node("timeline", node_timeline)
    graph.add_node("innovation", node_innovation)
    graph.add_node("research_gap", node_research_gap)
    graph.add_node("citation", node_citation)
    graph.add_node("general_chat", node_general_chat)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges("classify_intent", _route_by_intent, {
        "recommendation": "recommendation", "timeline": "timeline", "innovation": "innovation",
        "research_gap": "research_gap", "citation": "citation", "general_chat": "general_chat",
    })
    for node in ["recommendation", "timeline", "innovation", "research_gap", "citation", "general_chat"]:
        graph.add_edge(node, END)
    return graph.compile()


def run_planner_agent(db: Session, user_id: str, doc_id: str, question: str,
                       topic: str = "", research_gaps: str = "", run: AgentRun = None) -> AgentRun:
    run = run or start_run(db, user_id, doc_id, "planner", question)
    try:
        planner = _build_planner_graph()
        final_state = planner.invoke({
            "question": question, "doc_id": doc_id, "user_id": user_id, "topic": topic,
            "research_gaps": research_gaps, "intent": "", "result": {},
        })
        add_step(db, run, 0, "classify_intent", f"Classified intent: {final_state['intent']}",
                 detail={"intent": final_state["intent"]})
        add_step(db, run, 1, final_state["intent"], f"Ran the {final_state['intent'].replace('_', ' ')} tool",
                 detail=final_state["result"])
        # Flatten: the GUI looks for answer/recommendations/timeline/ideas/gaps
        # at the top level of `result` — nesting it under a "result" key (the
        # previous behavior) meant the panel could never find it and showed
        # a blank answer even though the planner had genuinely produced one.
        return finish_run(db, run, result_json={"intent": final_state["intent"], **final_state["result"]})
    except Exception as e:
        return finish_run(db, run, status="failed", error=str(e))