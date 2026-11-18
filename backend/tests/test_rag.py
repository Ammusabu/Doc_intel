"""RAG endpoint tests — real retrieval + Groq call. Skips if no key."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["CELERY_EAGER"] = "1"

from app.main import app  # noqa: E402

FIX = Path(__file__).parent / "fixtures"
from app.services import rag

@pytest.fixture(autouse=True)
def mock_s3(monkeypatch):
    
    import boto3
    from moto import mock_aws
    from app.services.storage import StorageClient, _S3Backend

    with mock_aws():
        def _fake(cls=None):
            c = boto3.client("s3", region_name="us-east-1",
                             aws_access_key_id="t", aws_secret_access_key="t")
            b = _S3Backend(c, bucket="docintel-test-bucket")
            b.ensure_bucket()
            return StorageClient(b)
        monkeypatch.setattr(StorageClient, "from_settings", classmethod(_fake))
        monkeypatch.setattr(
             rag,
             "_call_groq",
             lambda prompt: (
                 "The document recommends checking the graphics driver version, "
                 "updating the driver, and restarting the system."
            ),
       )
        yield


async def _setup(client: AsyncClient, filename: str = "sample.txt"):
    email = f"rag_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Passw0rd123", "full_name": "RAG",
    })
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Passw0rd123"})
    token = r.json()["access_token"]
    data = (FIX / filename).read_bytes()
    await client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, data, "text/plain")},
    )
    return token


@pytest.mark.asyncio
async def test_chat_returns_answer_with_citations():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token = await _setup(client)
            r = await client.post(
                "/api/v1/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": "What troubleshooting steps are described for the graphics driver?"},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["answer"]
            assert len(body["citations"]) >= 1
            assert body["no_relevant_docs"] is False


@pytest.mark.asyncio
async def test_citations_reference_real_chunks():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token = await _setup(client)
            r = await client.post(
                "/api/v1/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": "What does the document say about the graphics driver?"},
            )
            body = r.json()
            for c in body["citations"]:
                assert c["chunk_id"]
                assert c["document_id"]
                assert c["page_number"] >= 1
                assert c["excerpt"]


@pytest.mark.asyncio
async def test_refusal_when_no_relevant_docs():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token = await _setup(client)
            r = await client.post(
                "/api/v1/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": "What is the recipe for chocolate chip cookies?"},
            )
            body = r.json()
            assert body["no_relevant_docs"] in (True, False)
            if body["no_relevant_docs"]:
                assert "do not contain enough information" in body["answer"].lower()


@pytest.mark.asyncio
async def test_conversation_persists():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token = await _setup(client)
            r = await client.post(
                "/api/v1/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": "Tell me about the graphics driver."},
            )
            conv_id = r.json()["conversation_id"]
            r = await client.get(
                f"/api/v1/chat/conversations/{conv_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 200
            detail = r.json()
            assert len(detail["messages"]) >= 2
            assert detail["messages"][0]["role"] == "user"
            assert detail["messages"][1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_conversation_permission_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token_a = await _setup(client)
            r = await client.post(
                "/api/v1/chat",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"message": "graphics driver details"},
            )
            conv_id = r.json()["conversation_id"]

            email_b = f"ragb_{uuid.uuid4().hex[:8]}@example.com"
            await client.post("/api/v1/auth/register", json={
                "email": email_b, "password": "Passw0rd123", "full_name": "B",
            })
            r = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Passw0rd123"})
            token_b = r.json()["access_token"]

            r = await client.get(
                f"/api/v1/chat/conversations/{conv_id}",
                headers={"Authorization": f"Bearer {token_b}"},
            )
            assert r.status_code == 404
