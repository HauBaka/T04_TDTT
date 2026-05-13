from typing import Any, Dict

import boto3
from botocore.client import Config
from starlette.concurrency import run_in_threadpool

from core.settings import settings


class R2Client:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID.get_secret_value(),
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY.get_secret_value(),
            region_name=settings.R2_REGION,
            config=Config(signature_version="s3v4"),
        )

    async def generate_presigned_put_url(
        self, key: str, content_type: str, expires_in: int
    ) -> str:
        def _sign() -> str:
            return self._client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": settings.R2_BUCKET,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )

        return await run_in_threadpool(_sign)

    async def head_object(self, key: str) -> Dict[str, Any]:
        def _head() -> Dict[str, Any]:
            return self._client.head_object(
                Bucket=settings.R2_BUCKET,
                Key=key,
            )

        return await run_in_threadpool(_head)

    async def delete_object(self, key: str) -> None:
        def _delete() -> None:
            self._client.delete_object(
                Bucket=settings.R2_BUCKET,
                Key=key,
            )

        await run_in_threadpool(_delete)


r2_client = R2Client()
