from datetime import datetime, timezone
from google.cloud import firestore as fs

from core.database import get_db
from core.exceptions import AppException, NotFoundError
from schemas.collection_schema import ModifyAction

from repositories.base_repo import BaseRepository

class CollectionRepository(BaseRepository):
    def __init__(self):
        super().__init__("collections")

    async def create_collection(self, uid: str, collection_request: dict) -> dict:
        """Tạo một collection mới cho người dùng."""
        timestamp = datetime.now(timezone.utc)
        data = collection_request.copy()
        data.update({
            "owner_uid": uid,
            "created_at": timestamp,
            "updated_at": timestamp,
            "liked_count": 0,
            "contributor_count": 0,
            "place_count": 0,
            "collaborators": [],
            "places": [],
            "tags": data.get("tags") or [],
            "liked": [],
        })

        ref_id = await self._create(data)
        return await self.get_collection(ref_id)

    async def update_collection(
        self,
        collection_id: str,
        update_data: dict,
        requester_id: str | None = None,
        collaborator_additions: dict[str, dict] | None = None,
    ) -> dict:
        """Cập nhật một collection của người dùng."""
        ref = self._collection.document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        payload = {key: value for key, value in update_data.items() if value is not None}
        if not payload:
            return snapshot.to_dict() or {}
        
        payload["updated_at"] = datetime.now(timezone.utc)
        await ref.update(payload)

        updated_snapshot = await ref.get()
        collection_data = updated_snapshot.to_dict() or {}
        collection_data["id"] = ref.id
        return collection_data

    async def delete_collection(self, collection_id: str) -> bool:
        """Xóa một collection của người dùng."""
        return await self._delete(collection_id)

    async def get_collection(self, collection_id: str) -> dict:
        """Lấy thông tin của một collection cụ thể."""
        return await self._get_by_id(collection_id) or {}


collection_repo = CollectionRepository()