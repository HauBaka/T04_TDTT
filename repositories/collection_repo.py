from datetime import datetime, timezone
from weakref import ref
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
            "collaborators_count": 0,
            "place_count": 0,
            "tags": data.get("tags") or [],
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

    async def _delete_subcollection(self, sub_ref) -> None:
        batch = self._get_db().batch()
        count = 0

        async for doc in sub_ref.stream():
            batch.delete(doc.reference)
            count += 1

            if count == 500:
                await batch.commit()
                batch = self._get_db().batch()
                count = 0

        if count > 0:
            await batch.commit()

    async def delete_collection(self, collection_id: str) -> bool:
        """Xóa một collection của người dùng."""
        ref = self._collection.document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return False
        
        # Xóa sub-collections trước 
        await self._delete_subcollection(ref.collection("places"))
        await self._delete_subcollection(ref.collection("collaborators"))
        # Xóa main document
        batch = self._get_db().batch()
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

    async def add_places_to_collection(self, collection_id: str, place_ids: list[str], requester_id: str) -> dict:
        """Thêm nhiều địa điểm vào collection với lọc duplicate và check existence."""
        ref = self._collection.document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}
        
        # Lấy places hiện có
        places_collection = ref.collection("places")
        docs = self._get_db().get_all(
            [places_collection.document(pid) for pid in place_ids]
        )
        existing_docs = {doc.id async for doc in docs if doc.exists}
        # Lọc những place bị trùng lặp
        new_place_ids = [pid for pid in place_ids if pid not in existing_docs]
        
        if not new_place_ids:
            data = snapshot.to_dict() or {}
            data["id"] = ref.id
            return data
        
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
        
        # Update contributed_count của cộng tác viên
        collab_ref = ref.collection("collaborators").document(requester_id)
        batch.update(collab_ref, {
            "contributed_count": fs.Increment(len(new_place_ids))
        })

        # Update place_count trên main document
        batch.update(ref, {
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
        
        batch = self._get_db().batch()
        places_collection = ref.collection("places")
        # Lấy places hiện có
        docs_gen = self._get_db().get_all(
            [places_collection.document(pid) for pid in place_ids]
        )

        docs = [doc async for doc in docs_gen]
        existing_docs = {doc.id for doc in docs if doc.exists}
        if not existing_docs:
            data = snapshot.to_dict() or {}
            data["id"] = ref.id
            return data
        
        # Xóa những places được chỉ định
        timestamp = datetime.now(timezone.utc)
        
        for place_id in existing_docs:
            batch.delete(places_collection.document(place_id))
        
        # Update contributed_count của người đã thêm place
        for doc in docs:
            if doc.exists and doc.id in existing_docs:
                place_data = doc.to_dict() or {}
                added_by = place_data.get("added_by")
                if added_by:
                    collab_ref = ref.collection("collaborators").document(added_by)
                    batch.update(collab_ref, {
                        "contributed_count": fs.Increment(-1)
                    })


        # Update place_count trên main document
        batch.update(ref, {
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
        
        
        # Lưu collaborators vào sub-collection với structure: {uid: {contributed_count, joined_at}}
        timestamp = datetime.now(timezone.utc)
        batch = self._get_db().batch()
        collab_collection = ref.collection("collaborators")
        
        for uid in collaborator_uids:
            collab_ref = collab_collection.document(uid)
            batch.set(collab_ref, {
                "uid": uid,
                "contributed_count": 0,
                "joined_at": timestamp
            })
        
        # Update collaborators_count trên main document
        batch.update(ref, {
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
        
        # Update collaborators_count trên main document
        batch.update(ref, {
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