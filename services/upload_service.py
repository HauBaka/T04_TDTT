from datetime import datetime, timedelta, timezone
from typing import Dict

from core.exceptions import AppException, NotFoundError, ValidationError
from core.settings import settings
from externals.r2_client import r2_client
from repositories.upload_repo import upload_repo
from schemas.upload_schema import (
    UploadCategory,
    UploadConfirmRequest,
    UploadConfirmResponse,
    UploadCreateRequest,
    UploadPresignRequest,
    UploadPresignResponse,
    UploadStatus,
)

_ALLOWED_EXTENSIONS: Dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class UploadService:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id

    async def create_presigned_upload(
        self, request: UploadPresignRequest
    ) -> UploadPresignResponse:
        self._validate_file_size(request.file_size)
        self._validate_mime_type(request.content_type)

        file_key = self._build_object_key(
            category=request.category,
            content_type=request.content_type,
        )
        expires_in = settings.R2_PRESIGN_EXPIRE_SECONDS
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        upload_url = await r2_client.generate_presigned_put_url(
            key=file_key,
            content_type=request.content_type,
            expires_in=expires_in,
        )

        public_url = self._public_url(file_key)
        now = datetime.now(timezone.utc)

        await upload_repo.create_pending(
            UploadCreateRequest(
                user_id=self.user_id,
                file_key=file_key,
                content_type=request.content_type,
                file_size=request.file_size,
                category=request.category,
                status=UploadStatus.PENDING,
                created_at=now,
                expires_at=now + timedelta(minutes=settings.UPLOAD_PENDING_TTL_MINUTES),
                public_url=public_url,
            )
        )

        return UploadPresignResponse(
            upload_url=upload_url,
            file_key=file_key,
            public_url=public_url,
            expires_at=expires_at.isoformat(),
        )

    async def confirm_upload(
        self, request: UploadConfirmRequest
    ) -> UploadConfirmResponse:
        pending = await upload_repo.get_pending_by_key(self.user_id, request.file_key)
        if not pending:
            raise NotFoundError("Pending upload not found")

        expires_at = pending.expires_at
        if not expires_at:
            raise AppException("Invalid pending upload state", status_code=400)

        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at = expires_at.astimezone(timezone.utc)

        if expires_at <= datetime.now(timezone.utc):
            raise ValidationError("Pending upload has expired")

        head = await r2_client.head_object(request.file_key)

        size_bytes = int(head.get("ContentLength", 0))
        content_type = str(head.get("ContentType", ""))

        self._validate_file_size(size_bytes)

        expected_size = pending.file_size
        if expected_size is not None and size_bytes != int(expected_size):
            raise ValidationError("Uploaded file size mismatch")

        self._validate_mime_type(content_type)

        await upload_repo.mark_confirmed(
            doc_id=pending.id,
            user_id=self.user_id,
            file_key=request.file_key,
            update_data={
                "status": UploadStatus.CONFIRMED.value,
                "confirmed_at": datetime.now(timezone.utc),
                "etag": head.get("ETag"),
                "size_bytes": size_bytes,
                "content_type": content_type,
            },
        )

        return UploadConfirmResponse(
            file_key=request.file_key,
            public_url=self._public_url(request.file_key),
            size_bytes=size_bytes,
            content_type=content_type,
        )

    def _validate_file_size(self, file_size: int) -> None:
        max_bytes = settings.R2_MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size <= 0 or file_size > max_bytes:
            raise ValidationError(
                f"File size must be between 1 byte and {settings.R2_MAX_FILE_SIZE_MB} MB"
            )

    def _validate_mime_type(self, content_type: str) -> None:
        allowed = [
            mime.strip()
            for mime in settings.R2_ALLOWED_IMAGE_MIME_TYPES.split(",")
            if mime.strip()
        ]
        if content_type not in allowed:
            raise ValidationError("Unsupported file type")

    def _build_object_key(self, category: UploadCategory, content_type: str) -> str:
        extension = _ALLOWED_EXTENSIONS.get(content_type)
        if not extension:
            raise ValidationError("Unsupported file extension")

        now = datetime.now(timezone.utc)
        date_path = f"{now.year}/{now.month:02d}"
        unique_id = f"{self._uuid()}"

        return (
            f"uploads/{category.value}/"
            f"{self.user_id}/"
            f"{date_path}/"
            f"{unique_id}{extension}"
        )

    def _public_url(self, file_key: str) -> str:
        return f"https://{settings.R2_PUBLIC_CDN}/{file_key}"

    def _uuid(self) -> str:
        import uuid

        return uuid.uuid4().hex
