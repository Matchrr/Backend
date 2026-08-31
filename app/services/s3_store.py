"""Private S3 object store for source PDFs and compiled dossier files.

Xano holds the pointer (`s3_key`). This module is the only writer. Reads for
the browser are pre-signed GETs (15 minutes).
"""

from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

PRESIGN_SECONDS = 15 * 60
MAX_SOURCE_BYTES = 10 * 1024 * 1024


class S3StoreError(RuntimeError):
    pass


def configured() -> bool:
    return bool(settings.matchr_s3_bucket and settings.aws_access_key_id)


def source_key(user_id: int | str, sha256: str) -> str:
    return f"users/{user_id}/sources/{sha256}.pdf"


def user_prefix(user_id: int | str) -> str:
    return f"users/{user_id}/"


def put_source_pdf(
    *,
    user_id: int | str,
    sha256: str,
    body: bytes,
    kind: str,
) -> str:
    """Upload a source PDF. Same-hash re-upload is a no-op PUT of identical bytes."""
    if not configured():
        raise S3StoreError("MATCHR_S3_BUCKET is not configured")
    if len(body) > MAX_SOURCE_BYTES:
        raise S3StoreError("PDF exceeds the 10 MB upload cap")
    key = source_key(user_id, sha256)
    meta_kind = "linkedin_pdf" if kind == "linkedin_pdf" else "source_resume"
    try:
        _client().put_object(
            Bucket=settings.matchr_s3_bucket,
            Key=key,
            Body=body,
            ContentType="application/pdf",
            ServerSideEncryption="AES256",
            Metadata={"user-id": str(user_id), "kind": meta_kind},
        )
    except (BotoCoreError, ClientError) as exc:
        raise S3StoreError(f"S3 PUT failed: {exc}") from exc
    return key


def presigned_get(key: str) -> str:
    if not configured():
        raise S3StoreError("MATCHR_S3_BUCKET is not configured")
    try:
        return _client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.matchr_s3_bucket, "Key": key},
            ExpiresIn=PRESIGN_SECONDS,
        )
    except (BotoCoreError, ClientError) as exc:
        raise S3StoreError(f"S3 presign failed: {exc}") from exc


def delete_user_prefix(user_id: int | str) -> None:
    """Account wipe: delete every object under users/{user_id}/."""
    if not configured():
        return
    prefix = user_prefix(user_id)
    client = _client()
    bucket = settings.matchr_s3_bucket
    token: str | None = None
    deleted = 0
    try:
        while True:
            kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            page = client.list_objects_v2(**kwargs)
            keys = [{"Key": item["Key"]} for item in page.get("Contents") or [] if item.get("Key")]
            if keys:
                client.delete_objects(Bucket=bucket, Delete={"Objects": keys, "Quiet": True})
                deleted += len(keys)
            if not page.get("IsTruncated"):
                break
            token = page.get("NextContinuationToken")
    except (BotoCoreError, ClientError) as exc:
        raise S3StoreError(f"S3 prefix delete failed: {exc}") from exc
    if deleted:
        logger.info("Deleted %s S3 objects under %s", deleted, prefix)


def _client() -> BaseClient:
    kwargs: dict[str, Any] = {"region_name": settings.aws_region or "ca-central-1"}
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("s3", **kwargs)
