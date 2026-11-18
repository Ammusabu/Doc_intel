"""
Storage tests using moto (boto3 mock) — no real MinIO needed.

Strategy: bypass app.config entirely in tests. Create a boto3 client with
endpoint_url=None (default AWS endpoint, which moto intercepts) and wrap it
in StorageClient manually. Production still goes through `from_settings()`.
"""
from __future__ import annotations

import pytest

boto3 = pytest.importorskip("boto3")
moto = pytest.importorskip("moto")


@pytest.fixture
def mock_s3():
    """Start moto's mocked S3, wrap it in our StorageClient (bypassing settings)."""
    from moto import mock_aws
    from app.services.storage import StorageClient

    with mock_aws():
        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        s = StorageClient(client, bucket="docintel-test-bucket")
        s.ensure_bucket()
        yield s


def test_upload_download_roundtrip(mock_s3):
    payload = b"hello world, this is a test PDF content"
    mock_s3.upload_bytes(payload, "test/doc1.txt", content_type="text/plain")
    downloaded = mock_s3.download("test/doc1.txt")
    assert downloaded == payload


def test_delete_removes_object(mock_s3):
    from botocore.exceptions import ClientError
    mock_s3.upload_bytes(b"bye", "test/doc2.txt")
    mock_s3.delete("test/doc2.txt")
    with pytest.raises(ClientError):
        mock_s3.download("test/doc2.txt")
