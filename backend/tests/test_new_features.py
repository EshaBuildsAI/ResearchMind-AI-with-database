"""
Tests for the new features: email verification, password reset, 2FA,
admin dashboard, usage/plan limits, multi-document context, and the
WebSocket streaming agent path. Mocks the same three external calls as
test_full_flow.py (HuggingFace embeddings, OpenAI, Semantic Scholar/arXiv).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = "sqlite:///./test_new_features.db"
# Note: ADMIN_USERNAMES is monkeypatched per-test (settings.ADMIN_USERNAMES)
# rather than set here via os.environ, since the Settings() singleton is
# constructed at first import of app.core.config — which may happen via a
# different test module imported earlier in the same pytest session.

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models import User
from app.services import llm_service, vectorstore, research_search, email_service, totp_service

client = TestClient(app)

FAKE_CHUNKS = ["Transformers use self-attention.", "Attention mechanisms weight token importance."]


@pytest.fixture(autouse=True)
def mock_external(monkeypatch):
    monkeypatch.setattr(vectorstore, "add_document", lambda **kw: len(FAKE_CHUNKS))
    monkeypatch.setattr(vectorstore, "query", lambda *a, **kw: FAKE_CHUNKS)
    monkeypatch.setattr(vectorstore, "query_with_metadata", lambda *a, **kw: [
        {"text": FAKE_CHUNKS[0], "page": 1, "confidence": 87.3, "doc_id": "d1", "filename": "f1.txt"},
    ])
    monkeypatch.setattr(vectorstore, "get_full_document_text", lambda *a, **kw: " ".join(FAKE_CHUNKS))
    monkeypatch.setattr(vectorstore, "get_full_documents_text", lambda *a, **kw: " ".join(FAKE_CHUNKS))
    monkeypatch.setattr(vectorstore, "delete_document", lambda *a, **kw: None)
    monkeypatch.setattr(vectorstore, "delete_all_for_user", lambda *a, **kw: None)
    monkeypatch.setattr(llm_service, "generate", lambda prompt, max_tokens=2048: "Mocked answer.")
    monkeypatch.setattr(research_search, "search_related_papers", lambda *a, **kw: [])
    monkeypatch.setattr(research_search, "search_arxiv", lambda *a, **kw: [])
    # Don't actually try to load the cross-encoder model (no internet) —
    # reranker falls back gracefully anyway, but skip the slow attempt.
    from app.services import reranker_service
    monkeypatch.setattr(reranker_service, "rerank", lambda question, candidates: candidates)


def _register_and_login(username="testuser1"):
    client.post("/auth/register", json={
        "username": username, "email": f"{username}@test.com", "password": "testpass123",
    })
    resp = client.post("/auth/login", json={"identifier": username, "password": "testpass123"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["requires_2fa"] is False
    return body["access_token"]


def _upload_ready_doc(token, filename="doc.txt", content=b"Transformers and attention."):
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/documents/upload", headers=headers, files={"file": (filename, content, "text/plain")})
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]
    db = SessionLocal()
    from app.models import Document
    doc = db.query(Document).filter(Document.id == doc_id).first()
    doc.status = "ready"
    doc.chunk_count = len(FAKE_CHUNKS)
    db.commit()
    db.close()
    return doc_id


# ==================== Email verification ====================

def test_registration_creates_verification_token_and_sends_email(monkeypatch):
    sent = {}
    monkeypatch.setattr(email_service, "_send", lambda to, subject, html, text: sent.update(to=to, subject=subject))
    client.post("/auth/register", json={"username": "verifyuser1", "email": "verifyuser1@test.com", "password": "testpass123"})
    assert sent.get("to") == "verifyuser1@test.com"
    assert "Verify" in sent.get("subject", "")

    db = SessionLocal()
    user = db.query(User).filter(User.username == "verifyuser1").first()
    assert user.email_verified is False
    assert user.email_verification_token is not None
    token = user.email_verification_token
    db.close()

    resp = client.post("/auth/verify-email", json={"token": token})
    assert resp.status_code == 200

    db = SessionLocal()
    user = db.query(User).filter(User.username == "verifyuser1").first()
    assert user.email_verified is True
    assert user.email_verification_token is None
    db.close()


def test_verify_email_rejects_bad_token():
    resp = client.post("/auth/verify-email", json={"token": "not-a-real-token"})
    assert resp.status_code == 400


def test_resend_verification_does_not_leak_account_existence():
    r1 = client.post("/auth/resend-verification", json={"email": "doesnotexist@test.com"})
    r2 = client.post("/auth/resend-verification", json={"email": "verifyuser1@test.com"})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["message"] == r2.json()["message"]


# ==================== Password reset ====================

def test_forgot_and_reset_password_flow():
    _register_and_login("pwresetuser1")
    client.post("/auth/forgot-password", json={"email": "pwresetuser1@test.com"})

    db = SessionLocal()
    user = db.query(User).filter(User.username == "pwresetuser1").first()
    token = user.password_reset_token
    assert token is not None
    db.close()

    resp = client.post("/auth/reset-password", json={"token": token, "new_password": "newpass456"})
    assert resp.status_code == 200

    # old password should no longer work
    old = client.post("/auth/login", json={"identifier": "pwresetuser1", "password": "testpass123"})
    assert old.status_code == 401

    # new password should work
    new = client.post("/auth/login", json={"identifier": "pwresetuser1", "password": "newpass456"})
    assert new.status_code == 200


def test_reset_password_rejects_expired_or_missing_token():
    resp = client.post("/auth/reset-password", json={"token": "garbage", "new_password": "whatever1"})
    assert resp.status_code == 400


# ==================== Two-factor authentication ====================

def test_2fa_enable_confirm_and_login_flow():
    token = _register_and_login("totpuser1")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/auth/2fa/enable", headers=headers)
    assert resp.status_code == 200
    secret = resp.json()["secret"]
    assert resp.json()["qr_code_base64"]

    code = totp_service.pyotp.TOTP(secret).now() if hasattr(totp_service, "pyotp") else None
    import pyotp as _pyotp
    code = _pyotp.TOTP(secret).now()

    resp = client.post("/auth/2fa/confirm", headers=headers, json={"code": code})
    assert resp.status_code == 200

    # Now login should require 2FA
    login_resp = client.post("/auth/login", json={"identifier": "totpuser1", "password": "testpass123"})
    assert login_resp.status_code == 200
    body = login_resp.json()
    assert body["requires_2fa"] is True
    assert body["pending_token"]
    assert body.get("access_token") is None

    code2 = _pyotp.TOTP(secret).now()
    final = client.post("/auth/login/2fa", json={"pending_token": body["pending_token"], "code": code2})
    assert final.status_code == 200
    assert final.json()["access_token"]


def test_2fa_login_rejects_wrong_code():
    token = _register_and_login("totpuser2")
    headers = {"Authorization": f"Bearer {token}"}
    secret = client.post("/auth/2fa/enable", headers=headers).json()["secret"]
    import pyotp as _pyotp
    code = _pyotp.TOTP(secret).now()
    client.post("/auth/2fa/confirm", headers=headers, json={"code": code})

    login_resp = client.post("/auth/login", json={"identifier": "totpuser2", "password": "testpass123"})
    pending = login_resp.json()["pending_token"]

    bad = client.post("/auth/login/2fa", json={"pending_token": pending, "code": "000000"})
    assert bad.status_code == 400


def test_2fa_disable():
    token = _register_and_login("totpuser3")
    headers = {"Authorization": f"Bearer {token}"}
    secret = client.post("/auth/2fa/enable", headers=headers).json()["secret"]
    import pyotp as _pyotp
    code = _pyotp.TOTP(secret).now()
    client.post("/auth/2fa/confirm", headers=headers, json={"code": code})

    code2 = _pyotp.TOTP(secret).now()
    resp = client.post("/auth/2fa/disable", headers=headers, json={"code": code2})
    assert resp.status_code == 200

    login_resp = client.post("/auth/login", json={"identifier": "totpuser3", "password": "testpass123"})
    assert login_resp.json()["requires_2fa"] is False


# ==================== Admin dashboard ====================

def test_admin_bootstrap_and_stats(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "ADMIN_USERNAMES", ["adminuser1"])
    admin_token = _register_and_login("adminuser1")  # matches ADMIN_USERNAMES
    _register_and_login("regularuser1")
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.get("/auth/me", headers=headers)
    assert resp.json()["is_admin"] is True

    stats = client.get("/admin/stats", headers=headers)
    assert stats.status_code == 200
    body = stats.json()
    assert body["total_users"] >= 2
    assert "free" in body["users_by_plan"]

    users = client.get("/admin/users", headers=headers)
    assert users.status_code == 200
    assert any(u["username"] == "regularuser1" for u in users.json())


def test_non_admin_cannot_access_admin_routes():
    token = _register_and_login("nonadminuser1")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/admin/stats", headers=headers)
    assert resp.status_code == 403


def test_admin_can_change_user_plan(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "ADMIN_USERNAMES", ["adminuser1"])
    admin_token = _register_and_login("adminuser1")
    target_token = _register_and_login("planuser1")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    db = SessionLocal()
    target = db.query(User).filter(User.username == "planuser1").first()
    target_id = target.id
    db.close()

    resp = client.post(f"/admin/users/{target_id}/set-plan?plan=pro", headers=admin_headers)
    assert resp.status_code == 200

    target_headers = {"Authorization": f"Bearer {target_token}"}
    usage = client.get("/usage/summary", headers=target_headers)
    assert usage.json()["plan"] == "pro"


# ==================== Usage / plan limits ====================

def test_document_upload_limit_enforced(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "FREE_PLAN_MAX_DOCUMENTS", 1)
    token = _register_and_login("limituser1")
    _upload_ready_doc(token, filename="one.txt")

    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/documents/upload", headers=headers, files={"file": ("two.txt", b"second doc", "text/plain")})
    assert resp.status_code == 402


def test_chat_daily_limit_enforced(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "FREE_PLAN_CHAT_PER_DAY", 2)
    token = _register_and_login("limituser2")
    headers = {"Authorization": f"Bearer {token}"}

    r1 = client.post("/query/chat", headers=headers, json={"question": "hello one"})
    r2 = client.post("/query/chat", headers=headers, json={"question": "hello two"})
    r3 = client.post("/query/chat", headers=headers, json={"question": "hello three"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 402


# ==================== Multi-document context ====================

def test_multi_document_chat():
    token = _register_and_login("multidocuser1")
    doc1 = _upload_ready_doc(token, filename="doc1.txt")
    doc2 = _upload_ready_doc(token, filename="doc2.txt")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/query/chat", headers=headers,
                        json={"question": "compare these", "document_ids": [doc1, doc2]})
    assert resp.status_code == 200, resp.text


def test_multi_document_citation_agent():
    token = _register_and_login("multidocuser2")
    doc1 = _upload_ready_doc(token, filename="doc1.txt")
    doc2 = _upload_ready_doc(token, filename="doc2.txt")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/agents/citation", headers=headers,
                        json={"question": "what do these say?", "document_ids": [doc1, doc2]})
    assert resp.status_code == 200, resp.text
    assert resp.json()["document_ids"] == [doc1, doc2]


# ==================== Streaming (WebSocket) ====================

def test_streaming_agent_start_and_websocket():
    token = _register_and_login("streamuser1")
    doc_id = _upload_ready_doc(token)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/agents/stream?agent_type=research", headers=headers,
                        json={"question": "how does attention work?", "document_id": doc_id})
    assert resp.status_code == 200, resp.text
    run_id = resp.json()["run_id"]
    assert resp.json()["status"] == "running"

    # BackgroundTasks run synchronously under TestClient before the response
    # is returned to the test, so the run should already be finished by now.
    final = client.get(f"/agents/runs/{run_id}", headers=headers)
    assert final.json()["status"] == "done"

    with client.websocket_connect(f"/ws/agents/{run_id}?token={token}") as ws:
        data = ws.receive_json()
        assert data["type"] == "run_finished"
        assert data["status"] == "done"


def test_websocket_rejects_bad_token():
    token = _register_and_login("streamuser2")
    doc_id = _upload_ready_doc(token)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/agents/stream?agent_type=recommendation", headers=headers,
                        json={"question": "transformer efficiency"})
    run_id = resp.json()["run_id"]

    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/agents/{run_id}?token=garbage-token") as ws:
            ws.receive_json()
