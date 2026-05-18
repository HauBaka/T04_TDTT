import asyncio
from typing import Optional

from google.cloud.firestore_v1.base_query import FieldFilter
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import ValidationError
from core.cache import cache_get, cache_set, cache_delete, cache_key
from repositories.base_repo import BaseRepository
from schemas.upload_schema import UploadCreateRequest, UploadDocument, UploadStatus

class UploadRepository(BaseRepository):
    def __init__(self):
        super().__init__(collection_name="uploads")

    async def create_pending(self, data: UploadCreateRequest) -> str:
        doc_ref = self._collection.document()
        payload = data.model_dump(mode="json", exclude_none=False)
        await asyncio.gather(
            doc_ref.set(payload),
            cache_set(
                cache_key(
                    self.collection_name,
                    "pending",
                    data.user_id,
                    data.file_key,
                ),
                {
                    **payload,
                    "id": doc_ref.id,
                },
                ttl_seconds=300,
            )
        )

        return doc_ref.id

    async def get_pending_by_key(self, user_id: str, file_key: str) -> Optional[UploadDocument]:
        cache_key_pending = cache_key(
            self.collection_name,
            "pending",
            user_id,
            file_key,
        )

        cached = await cache_get(cache_key_pending)
        if cached is not None:
            try:
                return UploadDocument.model_validate(cached)
            except PydanticValidationError:
                await cache_delete(cache_key_pending)

        query = (
            self._collection.where(filter=FieldFilter("user_id", "==", user_id))
            .where(filter=FieldFilter("file_key", "==", file_key))
            .where(filter=FieldFilter("status", "==", UploadStatus.PENDING.value))
            .limit(1)
        )
        docs = [doc async for doc in query.stream()]
        if not docs:
            return None
        data = docs[0].to_dict() or {}
        data["id"] = docs[0].id

        await cache_set(
            cache_key_pending,
            data,
            ttl_seconds=300,
        )
        try:
            return UploadDocument.model_validate(data)
        except PydanticValidationError as e:
            raise ValidationError("Invalid upload data") from e

    async def mark_confirmed(
        self,
        doc_id: str,
        user_id: str,
        file_key: str,
        update_data: dict,
    ) -> None:
        await asyncio.gather(
            self._collection.document(doc_id).update(update_data),
            cache_delete(
                cache_key(
                    self.collection_name,
                    "pending",
                    user_id,
                    file_key,
                )
            )
        )

upload_repo = UploadRepository()