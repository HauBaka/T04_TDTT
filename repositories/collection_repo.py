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

    async def add_places_to_collection(self, collection_id: str, places: list[dict]) -> dict:
        """Thêm nhiều địa điểm vào collection."""
        ref = self._collection.document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        current_data = snapshot.to_dict() or {}
        current_places = current_data.get("places", [])
        
        # Thêm places mới
        current_places.extend(places)
        
        update_payload = {
            "places": current_places,
            "place_count": len(current_places),
            "updated_at": datetime.now(timezone.utc)
        }
        
        await ref.update(update_payload)
        updated_snapshot = await ref.get()
        collection_data = updated_snapshot.to_dict() or {}
        collection_data["id"] = ref.id
        return collection_data

    async def remove_places_from_collection(self, collection_id: str, place_ids: list[str]) -> dict:
        """Xóa nhiều địa điểm khỏi collection."""
        ref = self._collection.document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        current_data = snapshot.to_dict() or {}
        current_places = current_data.get("places", [])
        
        # Loại bỏ places
        remaining_places = [p for p in current_places if p.get("place_id") not in place_ids]
        
        update_payload = {
            "places": remaining_places,
            "place_count": len(remaining_places),
            "updated_at": datetime.now(timezone.utc)
        }
        
        await ref.update(update_payload)
        updated_snapshot = await ref.get()
        collection_data = updated_snapshot.to_dict() or {}
        collection_data["id"] = ref.id
        return collection_data

    async def add_collaborators_to_collection(self, collection_id: str, collaborators: list[dict]) -> dict:
        """Thêm nhiều cộng tác viên vào collection."""
        ref = self._collection.document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        current_data = snapshot.to_dict() or {}
        current_collaborators = current_data.get("collaborators", [])
        
        # Thêm collaborators mới, tránh duplicate
        existing_uids = {c.get("uid") for c in current_collaborators if isinstance(c, dict)}
        for collab in collaborators:
            if collab.get("uid") not in existing_uids:
                current_collaborators.append(collab)
        
        update_payload = {
            "collaborators": current_collaborators,
            "contributor_count": len(current_collaborators),
            "updated_at": datetime.now(timezone.utc)
        }
        
        await ref.update(update_payload)
        updated_snapshot = await ref.get()
        collection_data = updated_snapshot.to_dict() or {}
        collection_data["id"] = ref.id
        return collection_data

    async def remove_collaborators_from_collection(self, collection_id: str, collaborator_uids: list[str]) -> dict:
        """Xóa nhiều cộng tác viên khỏi collection."""
        ref = self._collection.document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        current_data = snapshot.to_dict() or {}
        current_collaborators = current_data.get("collaborators", [])
        
        # Loại bỏ collaborators
        remaining_collaborators = [c for c in current_collaborators if c.get("uid") not in collaborator_uids]
        
        update_payload = {
            "collaborators": remaining_collaborators,
            "contributor_count": len(remaining_collaborators),
            "updated_at": datetime.now(timezone.utc)
        }
        
        await ref.update(update_payload)
        updated_snapshot = await ref.get()
        collection_data = updated_snapshot.to_dict() or {}
        collection_data["id"] = ref.id
        return collection_data

    async def add_tags_to_collection(self, collection_id: str, new_tags: list[str]) -> dict:
        """Thêm nhiều tag vào collection."""
        ref = self._collection.document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        current_data = snapshot.to_dict() or {}
        current_tags = current_data.get("tags", [])
        
        # Thêm tags mới, tránh duplicate
        for tag in new_tags:
            if tag not in current_tags:
                current_tags.append(tag)
        
        update_payload = {
            "tags": current_tags,
            "updated_at": datetime.now(timezone.utc)
        }
        
        await ref.update(update_payload)
        updated_snapshot = await ref.get()
        collection_data = updated_snapshot.to_dict() or {}
        collection_data["id"] = ref.id
        return collection_data

    async def remove_tags_from_collection(self, collection_id: str, tags_to_remove: list[str]) -> dict:
        """Xóa nhiều tag khỏi collection."""
        ref = self._collection.document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        current_data = snapshot.to_dict() or {}
        current_tags = current_data.get("tags", [])
        
        # Loại bỏ tags
        remaining_tags = [t for t in current_tags if t not in tags_to_remove]
        
        update_payload = {
            "tags": remaining_tags,
            "updated_at": datetime.now(timezone.utc)
        }
        
        await ref.update(update_payload)
        updated_snapshot = await ref.get()
        collection_data = updated_snapshot.to_dict() or {}
        collection_data["id"] = ref.id
        return collection_data


collection_repo = CollectionRepository()