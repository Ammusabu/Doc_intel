"""
S3-compatible storage wrapper. Works identically against MinIO (dev) or AWS S3 (prod).
Only the endpoint_url / credentials change.

Interface:
    storage = StorageClient.from_settings()
    storage.ensure_bucket()
    storage.upload_fileobj(fileobj, key, content_type)
    storage.download(key) -> bytes
    storage.presigned_get(key, expires=3600) -> str (URL)
    storage.delete(key)
"""
from __future__ import annotations

import io
import logging
from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import get_settings

log = logging.getLogger("docintel.storage")


class StorageClient:
    def __init__(self, s3_client, bucket: str):
        self.s3 = s3_client
        self.bucket = bucket

    @classmethod
    def from_settings(cls) -> "StorageClient":
        s = get_settings()
        client = boto3.client(
            "s3",
            endpoint_url=s.STORAGE_ENDPOINT_URL or None,  # empty -> boto3 default AWS endpoint
            aws_access_key_id=s.STORAGE_ACCESS_KEY,
            aws_secret_access_key=s.STORAGE_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        return cls(client, s.STORAGE_BUCKET_NAME)

    def ensure_bucket(self) -> None:
        try:
            self.s3.head_bucket(Bucket=self.bucket)
            log.info("bucket exists: %s", self.bucket)
        except ClientError:
            self.s3.create_bucket(Bucket=self.bucket)
            log.info("bucket created: %s", self.bucket)

    def upload_fileobj(self, fileobj: BinaryIO, key: str, content_type: str = "application/octet-stream") -> None:
        self.s3.upload_fileobj(fileobj, self.bucket, key, ExtraArgs={"ContentType": content_type})

    def upload_bytes(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> None:
        self.upload_fileobj(io.BytesIO(data), key, content_type)

    def download(self, key: str) -> bytes:
        buf = io.BytesIO()
        self.s3.download_fileobj(self.bucket, key, buf)
        return buf.getvalue()

    def presigned_get(self, key: str, expires: int = 3600) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires,
        )

    def delete(self, key: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=key)
