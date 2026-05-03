from datetime import datetime, timezone
from google.cloud import firestore as fs
from loguru import logger

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
        ref = self._collection.document(collection_id)
        batch = self._get_db().batch()
        
        # Xóa sub-collections trước 
        places_ref = ref.collection("places")
        async for doc in places_ref.stream():
            batch.delete(doc.reference)
        
        collab_ref = ref.collection("collaborators")
        async for doc in collab_ref.stream():
            batch.delete(doc.reference)
        
        # Xóa main document
        batch.delete(ref)
        
        await batch.commit()
        return True

    async def get_collection(self, collection_id: str) -> dict:
        """Lấy thông tin của một collection cụ thể."""
        return await self._get_by_id(collection_id) or {}

    async def _get_places_from_subcollection(self, collection_id: str) -> dict[str, dict]:
        """Lấy danh sách places từ sub-collection."""
        try:
            places_ref = self._collection.document(collection_id).collection("places")
            places = {}
            async for doc in places_ref.stream():
                if doc.exists:
                    data = doc.to_dict() or {}
                    data["place_id"] = doc.id
                    places[doc.id] = data
            return places
        except Exception as e:
            logger.error(f"Error getting places from subcollection for collection {collection_id}: {str(e)}")
            return {}

    async def _get_collaborators_from_subcollection(self, collection_id: str) -> dict[str, dict]:
        """Lấy danh sách collaborators từ sub-collection."""
        try:
            collab_ref = self._collection.document(collection_id).collection("collaborators")
            collaborators = {}
            async for doc in collab_ref.stream():
                if doc.exists:
                    data = doc.to_dict() or {}
                    data["uid"] = doc.id
                    collaborators[doc.id] = data
            return collaborators
        except Exception as e:
            logger.error(f"Error getting collaborators from subcollection for collection {collection_id}: {str(e)}")
            return {}

    async def add_places_to_collection(self, collection_id: str, place_ids: list[str], requester_id: str, hotel_repo=None) -> dict:
        """Thêm nhiều địa điểm vào collection với lọc duplicate và check existence."""
        ref = self._collection.document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        # Lấy places hiện có
        existing_places = await self._get_places_from_subcollection(collection_id)
        existing_place_ids = set(existing_places.keys())
        
        # Lọc những place bị trùng lặp
        new_place_ids = [pid for pid in place_ids if pid not in existing_place_ids]
        
        if not new_place_ids:
            return snapshot.to_dict() or {}
        
        # Check xem places có tồn tại trong database không
        if hotel_repo:
            existing_hotels = await hotel_repo.get_hotels(new_place_ids)
            new_place_ids = [pid for pid in new_place_ids if pid in existing_hotels]
        
        if not new_place_ids:
            raise NotFoundError("None of the provided place IDs exist in the database.")
        
        # Lưu places vào sub-collection
        timestamp = datetime.now(timezone.utc)
        batch = self._get_db().batch()
        places_collection = ref.collection("places")
        
        for place_id in new_place_ids:
            place_ref = places_collection.document(place_id)
            batch.set(place_ref, {
                "place_id": place_id,
                "added_at": timestamp,
                "added_by": requester_id
            })
        
        # Update place_count trên main document
        total_places = len(existing_place_ids) + len(new_place_ids)
        batch.update(ref, {
            "place_count": total_places,
            "updated_at": timestamp
        })
        
        await batch.commit()
        
        # Lấy updated collection
        updated_snapshot = await ref.get()
        collection_data = updated_snapshot.to_dict() or {}
        collection_data["id"] = ref.id
        return collection_data

    async def remove_places_from_collection(self, collection_id: str, place_ids: list[str]) -> dict:
        """Xóa nhiều địa điểm khỏi collection từ sub-collection."""
        ref = self._collection.document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        # Lấy places hiện có
        existing_places = await self._get_places_from_subcollection(collection_id)
        
        # Xóa những places được chỉ định
        timestamp = datetime.now(timezone.utc)
        batch = self._get_db().batch()
        places_collection = ref.collection("places")
        
        for place_id in place_ids:
            if place_id in existing_places:
                place_ref = places_collection.document(place_id)
                batch.delete(place_ref)
        
        # Update place_count trên main document
        remaining_count = len(existing_places) - sum(1 for pid in place_ids if pid in existing_places)
        batch.update(ref, {
            "place_count": max(0, remaining_count),
            "updated_at": timestamp
        })
        
        await batch.commit()
        
        # Lấy updated collection
        updated_snapshot = await ref.get()
        collection_data = updated_snapshot.to_dict() or {}
        collection_data["id"] = ref.id
        return collection_data

    async def add_collaborators_to_collection(self, collection_id: str, collaborator_uids: list[str]) -> dict:
        """Thêm nhiều cộng tác viên vào collection và lưu vào sub-collection."""
        ref = self._collection.document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        # Lấy collaborators hiện có
        existing_collaborators = await self._get_collaborators_from_subcollection(collection_id)
        existing_uids = set(existing_collaborators.keys())
        
        # Lọc những uid bị trùng lặp
        new_uids = [uid for uid in collaborator_uids if uid not in existing_uids]
        
        if not new_uids:
            return snapshot.to_dict() or {}
        
        # Lưu collaborators vào sub-collection với structure: {uid: {contributed_count, joined_at}}
        timestamp = datetime.now(timezone.utc)
        batch = self._get_db().batch()
        collab_collection = ref.collection("collaborators")
        
        for uid in new_uids:
            collab_ref = collab_collection.document(uid)
            batch.set(collab_ref, {
                "uid": uid,
                "contributed_count": 0,
                "joined_at": timestamp
            })
        
        # Update contributor_count trên main document
        total_collaborators = len(existing_uids) + len(new_uids)
        batch.update(ref, {
            "contributor_count": total_collaborators,
            "updated_at": timestamp
        })
        
        await batch.commit()
        
        # Lấy updated collection
        updated_snapshot = await ref.get()
        collection_data = updated_snapshot.to_dict() or {}
        collection_data["id"] = ref.id
        return collection_data

    async def remove_collaborators_from_collection(self, collection_id: str, collaborator_uids: list[str]) -> dict:
        """Xóa nhiều cộng tác viên khỏi collection từ sub-collection."""
        ref = self._collection.document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        # Lấy collaborators hiện có
        existing_collaborators = await self._get_collaborators_from_subcollection(collection_id)
        
        # Xóa những collaborators được chỉ định
        timestamp = datetime.now(timezone.utc)
        batch = self._get_db().batch()
        collab_collection = ref.collection("collaborators")
        
        for uid in collaborator_uids:
            if uid in existing_collaborators:
                collab_ref = collab_collection.document(uid)
                batch.delete(collab_ref)
        
        # Update contributor_count trên main document
        remaining_count = len(existing_collaborators) - sum(1 for uid in collaborator_uids if uid in existing_collaborators)
        batch.update(ref, {
            "contributor_count": max(0, remaining_count),
            "updated_at": timestamp
        })
        
        await batch.commit()
        
        # Lấy updated collection
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
        
        # Dùng ArrayUnion để tránh duplicate tự động
        update_payload = {
            "tags": fs.ArrayUnion(new_tags),
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
        
        # Dùng ArrayRemove để xóa tags
        update_payload = {
            "tags": fs.ArrayRemove(tags_to_remove),
            "updated_at": datetime.now(timezone.utc)
        }
        
        await ref.update(update_payload)
        updated_snapshot = await ref.get()
        collection_data = updated_snapshot.to_dict() or {}
        collection_data["id"] = ref.id
        return collection_data


collection_repo = CollectionRepository()