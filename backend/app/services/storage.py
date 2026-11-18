"""
S3-compatible storage wrapper with local-disk fallback.

Behavior:
- STORAGE_ENDPOINT_URL set → real boto3 S3 (MinIO/AWS/R2).
- STORAGE_ENDPOINT_URL empty/None → local disk at ~/doc-intel/uploads/.

Same interface in both modes:
    storage.ensure_bucket()
    storage.upload_fileobj(fileobj, key, content_type)
    storage.upload_bytes(data, key, content_type)
    storage.download(key) -> bytes
    storage.presigned_get(key, expires) -> str (URL or file://)
    storage.delete(key)
"""
from __future__ import annotations

import io
import logging
import shutil
from pathlib import Path
from typing import BinaryIO, Union

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import get_settings

log = logging.getLogger("docintel.storage")

LOCAL_ROOT = Path.home() / "doc-intel" / "uploads"


class StorageClient:
    def __init__(self, backend: Union["_S3Backend", "_LocalBackend"]):
        self.backend = backend

    @classmethod
    def from_settings(cls) -> "StorageClient":
        s = get_settings()
        if not s.STORAGE_ENDPOINT_URL or not s.STORAGE_ENDPOINT_URL.strip():
            log.info("storage: local disk fallback at %s", LOCAL_ROOT)
            return cls(_LocalBackend(LOCAL_ROOT))
        log.info("storage: S3 backend at %s bucket=%s", s.STORAGE_ENDPOINT_URL, s.STORAGE_BUCKET_NAME)
        return cls(_S3Backend.from_settings())

    def ensure_bucket(self) -> None:
        self.backend.ensure_bucket()

    def upload_fileobj(self, fileobj: BinaryIO, key: str, content_type: str = "application/octet-stream") -> None:
        self.backend.upload_fileobj(fileobj, key, content_type)

    def upload_bytes(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> None:
        self.backend.upload_fileobj(io.BytesIO(data), key, content_type)

    def download(self, key: str) -> bytes:
        return self.backend.download(key)

    def presigned_get(self, key: str, expires: int = 3600) -> str:
        return self.backend.presigned_get(key, expires)

    def delete(self, key: str) -> None:
        self.backend.delete(key)


class _LocalBackend:
    def __init__(self, root: Path):
        self.root = root

    def ensure_bucket(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = key.replace("..", "_").lstrip("/")
        p = self.root / safe
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def upload_fileobj(self, fileobj: BinaryIO, key: str, content_type: str) -> None:
        with self._path(key).open("wb") as f:
            shutil.copyfileobj(fileobj, f)

    def download(self, key: str) -> bytes:
        p = self._path(key)
        if not p.exists():
            raise FileNotFoundError(f"storage key not found: {key}")
        return p.read_bytes()

    def presigned_get(self, key: str, expires: int) -> str:
        return f"file://{self._path(key)}"

    def delete(self, key: str) -> None:
        p = self._path(key)
        if p.exists():
            p.unlink()


class _S3Backend:
    def __init__(self, client, bucket: str):
        self.client = client
        self.bucket = bucket

    @classmethod
    def from_settings(cls) -> "_S3Backend":
        s = get_settings()
        client = boto3.client(
            "s3",
            endpoint_url=s.STORAGE_ENDPOINT_URL or None,
            aws_access_key_id=s.STORAGE_ACCESS_KEY,
            aws_secret_access_key=s.STORAGE_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        return cls(client, s.STORAGE_BUCKET_NAME)

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)

    def upload_fileobj(self, fileobj: BinaryIO, key: str, content_type: str) -> None:
        self.client.upload_fileobj(fileobj, self.bucket, key, ExtraArgs={"ContentType": content_type})

    def download(self, key: str) -> bytes:
        buf = io.BytesIO()
        self.client.download_fileobj(self.bucket, key, buf)
        return buf.getvalue()

    def presigned_get(self, key: str, expires: int) -> str:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires,
        )

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)
