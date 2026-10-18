"""Where the document goes: S3 when publishing is on, nowhere when it is off."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import anyio
import boto3

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class Publisher(Protocol):
    """Anything that can put the document somewhere. `target` names it for logs and health."""

    target: str

    async def publish(self, body: bytes) -> None: ...


class NullPublisher:
    """Dry run: the document is built, gated and served in-lab, never sent."""

    target = "dry-run"

    async def publish(self, body: bytes) -> None:
        return None


class S3Publisher:
    """PUTs the document to one key. The IAM user can write that prefix and nothing else."""

    def __init__(
        self,
        bucket: str,
        key: str,
        cache_control: str,
        region: str = "us-east-1",
        client: S3Client | None = None,
    ) -> None:
        if not bucket:
            raise ValueError("PUBLISH_ENABLED is true but S3_BUCKET is empty")
        self.bucket = bucket
        self.key = key
        self.cache_control = cache_control
        self.target = f"s3://{bucket}/{key}"
        self._client: S3Client = client or boto3.client("s3", region_name=region)

    async def publish(self, body: bytes) -> None:
        await anyio.to_thread.run_sync(self._put, body)

    def _put(self, body: bytes) -> None:
        self._client.put_object(
            Bucket=self.bucket,
            Key=self.key,
            Body=body,
            ContentType="application/json; charset=utf-8",
            CacheControl=self.cache_control,
        )
