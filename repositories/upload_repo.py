from typing import Optional

from google.cloud.firestore_v1.base_query import FieldFilter
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import ValidationError
from repositories.base_repo import BaseRepository
from schemas.upload_schema import UploadCreateRequest, UploadDocument, UploadStatus

class UploadRepository(BaseRepository):
    def __init__(self):
        super().__init__(collection_name="uploads")

    async def create_pending(self, data: UploadCreateRequest) -> str:
        doc_ref = self._collection.document()
        await doc_ref.set(data.model_dump(mode="python", exclude_none=False))
        return doc_ref.id

    async def get_pending_by_key(self, user_id: str, file_key: str) -> Optional[UploadDocument]:
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
        try:
            return UploadDocument.model_validate(data)
        except PydanticValidationError as e:
            raise ValidationError("Invalid upload data") from e

    async def mark_confirmed(self, doc_id: str, update_data: dict) -> None:
        await self._collection.document(doc_id).update(update_data)

upload_repo = UploadRepository()