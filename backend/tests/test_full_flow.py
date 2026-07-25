"""
Full-flow test suite. Mocks the three things this sandbox genuinely cannot
reach (HuggingFace embedding download, OpenAI, Semantic Scholar/arXiv/OpenAlex)
so every router, schema, guardrail, and rate-limit path still gets exercised
end-to-end. Real, unmocked calls to these three happen on the developer's
own machine with real network/keys — documented honestly, same as V3's roadmap.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = "sqlite:///./test_full_flow.db"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import llm_service, vectorstore, research_search

client = TestClient(app)

FAKE_CHUNKS = ["Transformers use self-attention.", "Attention mechanisms weight token importance."]
FAKE_PAPERS = [
    {"title": "Attention Is All You Need", "url": "https://arxiv.org/abs/1706.03762",
     "snippet": "We propose a new architecture, the Transformer.", "source": "Semantic Scholar", "year": 2017},
]


@pytest.fixture(autouse=True)
def mock_external(monkeypatch):
    monkeypatch.setattr(vectorstore, "add_document", lambda **kw: len(FAKE_CHUNKS))
    monkeypatch.setattr(vectorstore, "query", lambda *a, **kw: FAKE_CHUNKS)
    monkeypatch.setattr(vectorstore, "query_with_metadata", lambda *a, **kw: [
        {"text": FAKE_CHUNKS[0], "page": 1, "confidence": 87.3},
    ])
    monkeypatch.setattr(vectorstore, "get_full_document_text", lambda *a, **kw: " ".join(FAKE_CHUNKS))
    monkeypatch.setattr(vectorstore, "delete_document", lambda *a, **kw: None)
    monkeypatch.setattr(vectorstore, "delete_all_for_user", lambda *a, **kw: None)

    monkeypatch.setattr(llm_service, "generate", lambda prompt, max_tokens=2048: "This is a mocked GPT-4o-mini answer citing the document and related papers.")
    monkeypatch.setattr(research_search, "search_arxiv", lambda *a, **kw: FAKE_PAPERS)
    monkeypatch.setattr(research_search, "search_semantic_scholar", lambda *a, **kw: FAKE_PAPERS)
    monkeypatch.setattr(research_search, "search_openalex", lambda *a, **kw: [])
    monkeypatch.setattr(research_search, "search_related_papers", lambda *a, **kw: FAKE_PAPERS)


def _register_and_login(username="fulluser1"):
    client.post("/auth/register", json={
        "username": username, "email": f"{username}@test.com", "password": "testpass123",
    })
    resp = client.post("/auth/login", json={"identifier": username, "password": "testpass123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _upload_ready_doc(token, filename="doc.txt", content=b"Transformers and attention mechanisms."):
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/documents/upload", headers=headers, files={"file": (filename, content, "text/plain")})
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]
    # BackgroundTasks run inline under TestClient, but the real extractor
    # touches disk paths — force status to ready via the DB to test
    # downstream routes in isolation from the extraction step (extraction
    # itself is separately verified in test_document_processing.py).
    from app.core.database import SessionLocal
    from app.models import Document
    db = SessionLocal()
    doc = db.query(Document).filter(Document.id == doc_id).first()
    doc.status = "ready"
    doc.chunk_count = len(FAKE_CHUNKS)
    db.commit()
    db.close()
    return doc_id


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_auth_flow():
    token = _register_and_login("authuser1")
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "authuser1"

    resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_document_upload_and_isolation():
    token_a = _register_and_login("docuserA")
    token_b = _register_and_login("docuserB")
    doc_id = _upload_ready_doc(token_a)

    # Owner can see it
    resp = client.get(f"/documents/{doc_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 200

    # Another user CANNOT see it — this is the storage-level isolation guarantee
    resp = client.get(f"/documents/{doc_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404


def test_chat_rag():
    token = _register_and_login("chatuser1")
    doc_id = _upload_ready_doc(token)
    resp = client.post("/query/chat", headers={"Authorization": f"Bearer {token}"},
                        json={"question": "What is self-attention?", "document_id": doc_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "mocked GPT-4o-mini answer" in body["answer"]
    assert len(body["sources"]) == len(FAKE_CHUNKS)


def test_chat_guardrail_empty_question():
    token = _register_and_login("chatuser2")
    resp = client.post("/query/chat", headers={"Authorization": f"Bearer {token}"}, json={"question": "  "})
    assert resp.status_code == 400


def test_chat_rate_limit():
    token = _register_and_login("chatuser3")
    headers = {"Authorization": f"Bearer {token}"}
    codes = []
    for i in range(15):
        resp = client.post("/query/chat", headers=headers, json={"question": f"question number {i}"})
        codes.append(resp.status_code)
    assert 429 in codes, f"Expected a 429 once the per-minute limit was exceeded, got: {codes}"


def test_research_agent_full_pipeline():
    token = _register_and_login("agentuser1")
    doc_id = _upload_ready_doc(token)
    resp = client.post("/agents/research", headers={"Authorization": f"Bearer {token}"},
                        json={"question": "How does attention work?", "document_id": doc_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "done"
    assert body["agent_type"] == "research"
    step_names = [s["name"] for s in body["steps"]]
    assert step_names == ["retrieve_docs", "search_web", "synthesize"]
    assert body["result"]["sources"][0]["title"] == "Attention Is All You Need"


def test_citation_agent_page_numbers():
    token = _register_and_login("agentuser2")
    doc_id = _upload_ready_doc(token)
    resp = client.post("/agents/citation", headers={"Authorization": f"Bearer {token}"},
                        json={"question": "What is attention?", "document_id": doc_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["result"]["citations"][0]["page"] == 1
    assert body["result"]["citations"][0]["confidence"] == 87.3


def test_recommendation_and_timeline_agents_no_doc_needed():
    token = _register_and_login("agentuser3")
    resp = client.post("/agents/recommendation", headers={"Authorization": f"Bearer {token}"},
                        json={"question": "transformer architectures"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["result"]["sources"][0]["source"] == "Semantic Scholar"

    resp = client.post("/agents/timeline", headers={"Authorization": f"Bearer {token}"},
                        json={"question": "transformer architectures"})
    assert resp.status_code == 200, resp.text


def test_planner_agent_routes():
    token = _register_and_login("agentuser4")
    doc_id = _upload_ready_doc(token)
    resp = client.post("/agents/planner", headers={"Authorization": f"Bearer {token}"},
                        json={"question": "What papers should I read next on this topic?", "document_id": doc_id})
    assert resp.status_code == 200, resp.text
    # planner's intent classification also goes through the mocked llm_service.generate,
    # which always returns the same string — so intent falls back to general_chat.
    # What matters here is that routing + step persistence didn't crash.
    assert resp.json()["agent_type"] == "planner"
    assert len(resp.json()["steps"]) == 2


def test_summarize_reference_tool(monkeypatch):
    monkeypatch.setattr(research_search, "fetch_url_text", lambda url, max_chars=15000: "Some fetched page text about transformers.")
    monkeypatch.setattr(llm_service, "summarize_url_content", lambda url, text, question="": "A short mocked summary of the page.")
    token = _register_and_login("agentuser5")
    resp = client.post("/agents/summarize-reference", headers={"Authorization": f"Bearer {token}"},
                        json={"url": "https://arxiv.org/abs/1706.03762"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "done"
    assert "mocked summary" in body["result_text"]


def test_summarize_reference_rejects_bad_url():
    token = _register_and_login("agentuser6")
    resp = client.post("/agents/summarize-reference", headers={"Authorization": f"Bearer {token}"},
                        json={"url": "not-a-url"})
    assert resp.status_code == 400


def test_features_summary_quiz_flashcards(monkeypatch):
    monkeypatch.setattr(llm_service, "generate_summary", lambda text, length="medium": "- Point one\n- Point two")
    monkeypatch.setattr(llm_service, "generate_quiz", lambda text, n: [
        {"question": "Q1?", "options": {"A": "x", "B": "y", "C": "z", "D": "w"}, "correct": "A"}
    ])
    monkeypatch.setattr(llm_service, "generate_flashcards", lambda text, n: [{"front": "F", "back": "B"}])

    token = _register_and_login("featureuser1")
    doc_id = _upload_ready_doc(token)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/features/summary", headers=headers, json={"document_id": doc_id, "length": "short"})
    assert resp.status_code == 200 and "Point one" in resp.json()["summary"]

    resp = client.post("/features/quiz", headers=headers, json={"document_id": doc_id, "num_questions": 1})
    assert resp.status_code == 200 and resp.json()["questions"][0]["correct"] == "A"

    resp = client.post("/features/flashcards", headers=headers, json={"document_id": doc_id, "num_cards": 1})
    assert resp.status_code == 200 and resp.json()["cards"][0]["front"] == "F"


def test_features_require_ready_document():
    token = _register_and_login("featureuser2")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/documents/upload", headers=headers,
                        files={"file": ("d.txt", b"hello world", "text/plain")})
    doc_id = resp.json()["id"]
    # TestClient runs BackgroundTasks synchronously, so with mocked vectorstore
    # the doc reaches 'ready' almost instantly — force it back to 'processing'
    # here to test the "not ready yet" guard on the features routes in isolation.
    from app.core.database import SessionLocal
    from app.models import Document
    db = SessionLocal()
    doc = db.query(Document).filter(Document.id == doc_id).first()
    doc.status = "processing"
    db.commit()
    db.close()

    resp = client.post("/features/summary", headers=headers, json={"document_id": doc_id})
    assert resp.status_code == 409


def test_smart_memory_persists_across_research_agent_calls():
    token = _register_and_login("memuser1")
    doc_id = _upload_ready_doc(token)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/agents/research", headers=headers, json={"question": "Q1", "document_id": doc_id})
    resp = client.get(f"/features/smart-memory/{doc_id}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["entries"]) == 1
    assert resp.json()["entries"][0]["question"] == "Q1"


def test_reset_workspace_clears_everything():
    token = _register_and_login("resetuser1")
    headers = {"Authorization": f"Bearer {token}"}
    doc_id = _upload_ready_doc(token)
    client.post("/query/chat", headers=headers, json={"question": "hi", "document_id": doc_id})

    resp = client.post("/auth/reset-workspace", headers=headers)
    assert resp.status_code == 200

    resp = client.get("/documents", headers=headers)
    assert resp.json() == []


def test_delete_account_cascades():
    token = _register_and_login("deluser1")
    headers = {"Authorization": f"Bearer {token}"}
    _upload_ready_doc(token)
    resp = client.delete("/auth/account", headers=headers)
    assert resp.status_code == 200
    # token should no longer resolve to a user
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 401
