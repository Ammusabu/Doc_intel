"""Storage tests via moto — no real S3 needed."""
from __future__ import annotations

import pytest

pytest.importorskip("moto")
pytest.importorskip("boto3")


@pytest.fixture
def mock_s3():
    import boto3
    from moto import mock_aws
    from app.services.storage import StorageClient, _S3Backend

    with mock_aws():
        client = boto3.client(
            "s3", region_name="us-east-1",
            aws_access_key_id="test", aws_secret_access_key="test",
        )
        backend = _S3Backend(client, bucket="docintel-test-bucket")
        backend.ensure_bucket()
        yield StorageClient(backend)


def test_upload_download_roundtrip(mock_s3):
    payload = b"hello world, this is a test PDF content"
    mock_s3.upload_bytes(payload, "test/doc1.txt", content_type="text/plain")
    assert mock_s3.download("test/doc1.txt") == payload


def test_delete_removes_object(mock_s3):
    from botocore.exceptions import ClientError
    mock_s3.upload_bytes(b"bye", "test/doc2.txt")
    mock_s3.delete("test/doc2.txt")
    with pytest.raises(ClientError):
        mock_s3.download("test/doc2.txt")
