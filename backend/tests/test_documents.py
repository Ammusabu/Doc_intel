"""
End-to-end upload → process → retrieve flow.
Celery runs eagerly (no Redis). Storage is mocked with moto (no MinIO).
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["CELERY_EAGER"] = "1"  # must precede app imports

from app.main import app  # noqa: E402

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def mock_s3(monkeypatch):
    """Replace StorageClient.from_settings with a moto-backed instance for the whole test."""
    import boto3
    from moto import mock_aws
    from app.services.storage import StorageClient

    with mock_aws():
        def _fake_from_settings(cls=None):
            client = boto3.client(
                "s3", region_name="us-east-1",
                aws_access_key_id="test", aws_secret_access_key="test",
            )
            s = StorageClient(client, bucket="docintel-test-bucket")
            s.ensure_bucket()
            return s

        monkeypatch.setattr(StorageClient, "from_settings", classmethod(_fake_from_settings))
        yield


async def _register_and_login(client: AsyncClient) -> str:
    email = f"doctest_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Passw0rd!", "full_name": "Doc Test",
    })
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Passw0rd!"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_upload_process_and_list_txt():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token = await _register_and_login(client)
            headers = {"Authorization": f"Bearer {token}"}

            data = (FIX / "sample.txt").read_bytes()
            r = await client.post(
                "/api/v1/documents", headers=headers,
                files={"file": ("sample.txt", data, "text/plain")},
            )
            assert r.status_code == 202, r.text
            doc_id = r.json()["id"]

            r = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
            assert r.status_code == 200
            doc = r.json()
            print(f"[debug] doc status: {doc['status']}, error: {doc.get('error_message')}")
            assert doc["status"] in ("completed", "processing", "pending")

            r = await client.get("/api/v1/documents", headers=headers)
            assert r.status_code == 200
            body = r.json()
            assert body["total"] >= 1
            assert any(item["id"] == doc_id for item in body["items"])


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_extension():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token = await _register_and_login(client)
            r = await client.post(
                "/api/v1/documents",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")},
            )
            assert r.status_code == 400


@pytest.mark.asyncio
async def test_delete_document():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            token = await _register_and_login(client)
            headers = {"Authorization": f"Bearer {token}"}
            data = (FIX / "sample.txt").read_bytes()
            r = await client.post(
                "/api/v1/documents", headers=headers,
                files={"file": ("sample.txt", data, "text/plain")},
            )
            assert r.status_code == 202
            doc_id = r.json()["id"]
            r = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
            assert r.status_code == 204
            r = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
            assert r.status_code == 404
