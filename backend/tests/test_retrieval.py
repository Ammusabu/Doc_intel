"""
Retrieval tests — real embeddings, real reranker, moto-backed storage.
Uses Celery eager mode so uploads complete synchronously.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["CELERY_EAGER"] = "1"

from app.main import app  # noqa: E402

FIX = Path(__file__).parent / "fixtures"


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
        yield


async def _setup_user_with_doc(client: AsyncClient, filename: str = "sample.txt") -> tuple[str, str]:
    email = f"ret_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Passw0rd123", "full_name": "Ret",
    })
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Passw0rd123"})
    token = r.json()["access_token"]

    data = (FIX / filename).read_bytes()
    r = await client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, data, "text/plain")},
    )
    assert r.status_code == 202, r.text
    doc_id = r.json()["id"]
    return token, doc_id


@pytest.mark.asyncio
async def test_dense_returns_relevant_chunk():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token, _ = await _setup_user_with_doc(client)
            r = await client.post(
                "/api/v1/search",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": "graphics driver initialization", "top_k": 5, "use_reranker": False},
            )
            assert r.status_code == 200, r.text
            results = r.json()["results"]
            assert len(results) >= 1
            assert any("graphics" in r["content"].lower() for r in results)


@pytest.mark.asyncio
async def test_keyword_returns_relevant_chunk():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token, _ = await _setup_user_with_doc(client)
            r = await client.post(
                "/api/v1/search",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": "firmware revision", "top_k": 5, "use_reranker": False},
            )
            assert r.status_code == 200
            results = r.json()["results"]
            assert len(results) >= 1
            assert any(r["keyword_score"] is not None for r in results)


@pytest.mark.asyncio
async def test_hybrid_returns_rrf_score():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token, _ = await _setup_user_with_doc(client)
            r = await client.post(
                "/api/v1/search",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": "kernel module hardware", "top_k": 5, "use_reranker": False},
            )
            results = r.json()["results"]
            assert len(results) >= 1
            assert all(r["rrf_score"] > 0 for r in results)
            scores = [r["rrf_score"] for r in results]
            assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_reranker_produces_rerank_score():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token, _ = await _setup_user_with_doc(client)
            r = await client.post(
                "/api/v1/search",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": "troubleshooting display output", "top_k": 5, "use_reranker": True},
            )
            results = r.json()["results"]
            assert len(results) >= 1
            assert all(r["rerank_score"] is not None for r in results)


@pytest.mark.asyncio
async def test_filter_by_document_id_restricts_results():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token, doc_id = await _setup_user_with_doc(client)
            r = await client.post(
                "/api/v1/search",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "query": "graphics", "top_k": 5,
                    "document_id": doc_id, "use_reranker": False,
                },
            )
            results = r.json()["results"]
            for hit in results:
                assert hit["document_id"] == doc_id


@pytest.mark.asyncio
async def test_empty_query_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token, _ = await _setup_user_with_doc(client)
            r = await client.post(
                "/api/v1/search",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": "", "top_k": 5},
            )
            assert r.status_code == 422
