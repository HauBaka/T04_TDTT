from datetime import datetime, timezone
from core.database import get_db
from google.cloud import firestore

class CollectionRepository:
    def __init__(self):
        self.collection_name = "collections"

    def _get_db(self):
        return get_db()

    async def create_collection(self, uid: str, collection_request: dict) -> dict:
        """Tạo một collection mới cho người dùng."""
        ref = self._get_db().collection(self.collection_name).document()
        timestamp = datetime.now(timezone.utc)

        data = collection_request.copy()
        data["owner_uid"] = uid
        data["created_at"] = timestamp
        data["updated_at"] = timestamp

        await ref.set(data)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        collection_data = snapshot.to_dict()
        collection_data["id"] = ref.id
        return collection_data

    async def update_collection(self, uid: str, collection_id: str, update_data: dict) -> dict:
        """Cập nhật một collection của người dùng."""
        ref = self._get_db().collection(self.collection_name).document(collection_id)
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

    async def delete_collection(self, uid: str, collection_id: str):
        """Xóa một collection của người dùng."""
        ref = self._get_db().collection(self.collection_name).document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return False
        
        await ref.delete()
        return True

    async def get_collection(self, collection_id: str) -> dict:
        """Lấy thông tin của một collection cụ thể."""
        ref = self._get_db().collection(self.collection_name).document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        collection_data = snapshot.to_dict() or {}
        collection_data["id"] = ref.id
        return collection_data
    
collection_repo = CollectionRepository()