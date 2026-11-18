"""End-to-end upload -> process -> retrieve, moto-backed storage, eager Celery."""
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
        def _fake_from_settings(cls=None):
            client = boto3.client(
                "s3", region_name="us-east-1",
                aws_access_key_id="test", aws_secret_access_key="test",
            )
            backend = _S3Backend(client, bucket="docintel-test-bucket")
            backend.ensure_bucket()
            return StorageClient(backend)

        monkeypatch.setattr(StorageClient, "from_settings", classmethod(_fake_from_settings))
        yield


async def _register_and_login(client: AsyncClient) -> str:
    email = f"doctest_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Passw0rd123", "full_name": "Doc Test",
    })
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Passw0rd123"})
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
            print(f"[debug] status={doc['status']} category={doc.get('predicted_category')}")
            assert doc["status"] == "completed"
            assert doc["predicted_category"] is not None
            r = await client.get("/api/v1/documents", headers=headers)
            assert r.status_code == 200
            assert r.json()["total"] >= 1


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
