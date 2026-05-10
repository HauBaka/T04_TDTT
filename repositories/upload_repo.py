from typing import Any, Dict, Optional

from repositories.base_repo import BaseRepository
from schemas.upload_schema import UploadStatus
from google.cloud.firestore_v1.base_query import FieldFilter

class UploadRepository(BaseRepository):
    def __init__(self):
        super().__init__(collection_name="uploads")

    async def create_pending(self, data: Dict[str, Any]) -> str:
        doc_ref = self._collection.document()
        await doc_ref.set(data)
        return doc_ref.id

    async def get_pending_by_key(self, user_id: str, file_key: str) -> Optional[Dict[str, Any]]:
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
        return data

    async def mark_confirmed(self, doc_id: str, update_data: Dict[str, Any]) -> None:
        await self._collection.document(doc_id).update(update_data)

upload_repo = UploadRepository()