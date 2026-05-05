import asyncio
from google.cloud import firestore as fs
from datetime import datetime, timezone
from repositories.user_repo import user_repo
from repositories.hotel_repo import hotel_repo
from schemas.collection_schema import CollectionPublic, CollectionResponse, CollectionVisibility, CollectionPlace, CollectionCollaborator
from repositories.collection_repo import collection_repo
from core.exceptions import AppException, NotFoundError
from schemas.response_schema import ResponseSchema
from services.invitation_service import invitation_service
from services.notification_service import notification_service

class CollectionService:
    def __init__(self):
        self.collection_repo = collection_repo

    async def create_collection(self, user_id: str, collection_data: dict) -> ResponseSchema[CollectionResponse]:
        """Tạo một collection mới cho người dùng."""
        created_collection = await collection_repo.create_collection(user_id, collection_data)
        
        if not created_collection:
            raise AppException(status_code=500, message="Failed to create collection.")
        await self.add_collaborators_to_collection(created_collection["id"], user_id, [user_id])

        return await self.build_response(created_collection)
    
    async def get_collection(self, collection_id: str, requester_id: str | None) -> ResponseSchema[CollectionResponse]:
        """Lấy thông tin của một collection cụ thể."""
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        places_dict, collaborators_dict = await asyncio.gather(
            self.collection_repo._get_places_from_subcollection(collection_id),
            self.collection_repo._get_collaborators_from_subcollection(collection_id)
        )
        
        visibility = CollectionVisibility(collection.get("visibility", CollectionVisibility.PUBLIC.value))
        owner_uid = collection.get("owner_uid", "")
        collaborator_uids = collaborators_dict

        if visibility == CollectionVisibility.PRIVATE:
            if requester_id != owner_uid and requester_id not in collaborator_uids:
                raise AppException(status_code=403, message="You do not have permission to view this collection.")
        
        collection["places"] = list(places_dict.values())
        collection["collaborators"] = list(collaborators_dict.values())

        return await self.build_response(collection)
    
    async def update_collection(self, collection_id: str, requester_id: str, update_data: dict) -> ResponseSchema[CollectionResponse]:
        """Cập nhật thông tin của một collection. Chỉ owner mới có thể cập nhật."""

        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check requester - chỉ owner mới có thể update
        owner_uid = collection.get("owner_uid", "")
        if requester_id != owner_uid:
            raise AppException(status_code=403, message="You do not have permission to edit this collection.")
        
        # check changes
        for field in ["name", "description", "visibility", "thumbnail_url"]:
            if field in update_data and str(update_data[field]).strip() == str(collection.get(field, "")).strip():
                del update_data[field]  # Remove unchanged fields

        # Nếu không có trường nào hợp lệ để cập nhật, trả về lỗi
        if "name" not in update_data and "description" not in update_data and "visibility" not in update_data and "thumbnail_url" not in update_data:
            raise AppException(status_code=400, message="No valid fields to update.")
        
        # Check requester user exists
        requester = await user_repo.get_user(requester_id)
        if not requester:
            raise NotFoundError("User not found.")

        # So sánh với default liked collection
        if collection.get("id") == requester.get("liked_collection", ""):
            if "name" in update_data and str(update_data["name"]).strip().lower() != "liked":
                raise AppException(status_code=403, message="Cannot change the name of the default collection.")
        
        updated_data = await collection_repo.update_collection(collection_id, update_data)
        if not updated_data:
            raise AppException(status_code=500, message="Failed to update collection.")
        
        return await self.build_response(updated_data)
        
    async def add_places_to_collection(self, collection_id: str, requester_id: str, place_ids: list[str]) -> ResponseSchema[CollectionResponse]:
        """Thêm nhiều địa điểm vào một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check quyền
        owner_uid = collection.get("owner_uid", "")
        collaborators = await self.collection_repo._get_collaborators_from_subcollection(collection_id)
        collaborators_ids = collaborators
        
        if requester_id != owner_uid and requester_id not in collaborators_ids:
            raise AppException(status_code=403, message="You do not have permission to edit this collection.")
        
        # Check place_ids có tồn tại không
        valid_ids = await hotel_repo.valid_ids(place_ids)
        if not valid_ids:
            raise NotFoundError("None of the provided place IDs are valid.")

        # Thêm vào collection (với lọc duplicate, check existence, lưu vào sub-collection)
        updated_collection = await collection_repo.add_places_to_collection(
            collection_id, 
            valid_ids, 
            requester_id
        )
        if not updated_collection:
            raise AppException(status_code=500, message="Failed to add places to collection.")
        
        return await self.build_response(updated_collection)

    async def remove_places_from_collection(self, collection_id: str, requester_id: str, place_ids: list[str]) -> ResponseSchema[CollectionResponse]:
        """Xóa nhiều địa điểm khỏi một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check quyền
        owner_uid = collection.get("owner_uid", "")
        collaborators = await self.collection_repo._get_collaborators_from_subcollection(collection_id)
        collaborators_ids = collaborators

        if requester_id != owner_uid and requester_id not in collaborators_ids:
            raise AppException(status_code=403, message="You do not have permission to edit this collection.")
        
        # Xóa từ collection
        updated_collection = await collection_repo.remove_places_from_collection(collection_id, place_ids)
        if not updated_collection:
            raise AppException(status_code=500, message="Failed to remove places from collection.")
        
        return await self.build_response(updated_collection)
    
    async def add_collaborators_to_collection(self, collection_id: str, requester_id: str, collaborator_uids: list[str]) -> ResponseSchema[CollectionResponse]:
        """Thêm nhiều cộng tác viên vào một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check quyền - chỉ owner mới có thể thêm collaborators
        owner_uid = collection.get("owner_uid", "")
        if requester_id != owner_uid:
            raise AppException(status_code=403, message="You do not have permission to add collaborators to this collection.")
        
        # Validate người dùng tồn tại
        if collaborator_uids:
            existing_users = await user_repo.get_users(collaborator_uids)
            existing_uids = set(existing_users.keys())
            not_found_uids = [uid for uid in collaborator_uids if uid not in existing_uids]
            if not_found_uids:
                raise NotFoundError(f"Invalid collaborator UIDs: {', '.join(not_found_uids)}")
                # Lấy collaborators hiện có
        existing_collaborators = await self.collection_repo._get_collaborators_from_subcollection(collection_id)
        existing_uids = set(existing_collaborators.keys())
        
        # Lọc những uid bị trùng lặp
        new_uids = [uid for uid in collaborator_uids if uid not in existing_uids]
        
        if not new_uids:
            raise AppException(status_code=400, message="All provided collaborators are already added to the collection.")

        # Thêm vào collection (lưu vào sub-collection với uid, contributed_count, joined_at)
        updated_collection = await collection_repo.add_collaborators_to_collection(collection_id, new_uids)
        if not updated_collection:
            raise AppException(status_code=500, message="Failed to add collaborators to collection.")
        
        return await self.build_response(updated_collection)

    async def remove_collaborators_from_collection(self, collection_id: str, requester_id: str, collaborator_uids: list[str]) -> ResponseSchema[CollectionResponse]:
        """Xóa nhiều cộng tác viên khỏi một collection. Tránh xóa owner."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check quyền - chỉ owner mới có thể xóa collaborators
        owner_uid = collection.get("owner_uid", "")
        if requester_id != owner_uid:
            raise AppException(status_code=403, message="You do not have permission to remove collaborators from this collection.")
        
        # Kiểm tra không xóa owner
        if owner_uid in collaborator_uids:
            raise AppException(status_code=403, message="Cannot remove the owner from collaborators.")
        
        # Xóa từ collection
        updated_collection = await collection_repo.remove_collaborators_from_collection(collection_id, collaborator_uids)
        if not updated_collection:
            raise AppException(status_code=500, message="Failed to remove collaborators from collection.")
        
        return await self.build_response(updated_collection)
    
    async def add_tags_to_collection(self, collection_id: str, requester_id: str, tags: list[str]) -> ResponseSchema[CollectionResponse]:
        """Thêm nhiều tag vào một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check quyền
        owner_uid = collection.get("owner_uid", "")
        collaborators = await self.collection_repo._get_collaborators_from_subcollection(collection_id)
        collaborators_ids = collaborators

        if requester_id != owner_uid and requester_id not in collaborators_ids:
            raise AppException(status_code=403, message="You do not have permission to edit this collection.")
        
        # Thêm tags
        updated_collection = await collection_repo.add_tags_to_collection(collection_id, tags)
        if not updated_collection:
            raise AppException(status_code=500, message="Failed to add tags to collection.")
        
        return await self.build_response(updated_collection)

    async def remove_tags_from_collection(self, collection_id: str, requester_id: str, tags: list[str]) -> ResponseSchema[CollectionResponse]:
        """Xóa nhiều tag khỏi một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check quyền
        owner_uid = collection.get("owner_uid", "")
        collaborators = await self.collection_repo._get_collaborators_from_subcollection(collection_id)
        collaborators_ids = collaborators
        
        if requester_id != owner_uid and requester_id not in collaborators_ids:
            raise AppException(status_code=403, message="You do not have permission to edit this collection.")
        
        # Xóa tags
        updated_collection = await collection_repo.remove_tags_from_collection(collection_id, tags)
        if not updated_collection:
            raise AppException(status_code=500, message="Failed to remove tags from collection.")
        
        return await self.build_response(updated_collection)    

    async def delete_collection(self, collection_id: str, requester_id: str) -> ResponseSchema[bool]:
        """Xóa một collection."""
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check requester 
        requester = await user_repo.get_user(requester_id)
        if not requester:
            raise NotFoundError("User not found.")

        owner_uid = collection.get("owner_uid", "")
        if requester_id != owner_uid:
            raise AppException(status_code=403, message="You do not have permission to delete this collection.")
        
        if collection.get("id") == requester.get("liked_collection", ""):
            raise AppException(status_code=403, message="Cannot delete the default 'liked' collection.")
        
        return ResponseSchema(data=await collection_repo.delete_collection(collection_id))
    
    async def build_response(self, collection_data: dict) -> ResponseSchema[CollectionResponse]:
        """Xây dựng response cho collection."""
        if not collection_data:
            raise NotFoundError("Invalid collection ID.")
        
        collection_id = collection_data.get("id", "")
        
        if "places" not in collection_data or "collaborators" not in collection_data:
            places, collaborators = await asyncio.gather(
                self.collection_repo._get_places_from_subcollection(collection_id),
                self.collection_repo._get_collaborators_from_subcollection(collection_id)
            )
            collection_data["places"] = list(places.values())
            collection_data["collaborators"] = list(collaborators.values())

        collection = CollectionPublic(
            id = collection_data.get("id", ""),
            owner_uid = collection_data.get("owner_uid", ""),
            name = collection_data.get("name", ""),
            description = collection_data.get("description", ""),
            thumbnail_url = collection_data.get("thumbnail_url", None),
            created_at = collection_data.get("created_at", datetime.now(timezone.utc)),
            updated_at = collection_data.get("updated_at", datetime.now(timezone.utc)),
            saved_count = collection_data.get("saved_count", 0),
            savers = collection_data.get("savers", []),
            collaborators = collection_data.get("collaborators", []),
            places = collection_data.get("places", []),
            tags = collection_data.get("tags", []),
            visibility = CollectionVisibility(collection_data.get("visibility", "public"))
        )
        return ResponseSchema(data=CollectionResponse(collection=collection))

    async def save_collection(self, collection_id: str, requester_id: str) -> ResponseSchema[bool]:
        """Lưu một collection vào danh sách đã lưu của người dùng."""
        # Check collection tồn tại
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check user tồn tại
        user = await user_repo.get_user(requester_id)
        if not user:
            raise NotFoundError("User not found.")
        
        # Batch update:
        # > collections/{collection_id}/savers (sub-collection) thêm uid, saved_at
        # > users/{uid}/saved_collections (array) thêm collection_id
        # > collection.saved_count tăng 1

        saver_ref = collection_repo._collection.document(collection_id).collection("savers").document(requester_id)
        saver_snapshot = await saver_ref.get()
        if saver_snapshot.exists:
            raise AppException(status_code=400, message="Collection already saved.")
        
        db = collection_repo._get_db()
        batch = db.batch()
        timestamp = datetime.now(timezone.utc)
        
        collection_ref = collection_repo._collection.document(collection_id)
        user_ref = user_repo._collection.document(requester_id)
        
        # Thêm vào savers sub-collection
        saver_ref = collection_ref.collection("savers").document(requester_id)
        batch.set(saver_ref, {
            "uid": requester_id,
            "saved_at": timestamp
        })
        
        # Thêm collection_id vào saved_collections array của user
        batch.update(user_ref, {
            "saved_collections": fs.ArrayUnion([collection_id])
        })
        
        # Tăng saved_count
        batch.update(collection_ref, {
            "saved_count": fs.Increment(1),
            "updated_at": timestamp
        })
        
        await batch.commit()
        return ResponseSchema(data=True)
    
    async def unsave_collection(self, collection_id: str, requester_id: str) -> ResponseSchema[bool]:
        """Bỏ lưu một collection khỏi danh sách đã lưu của người dùng."""
        # Check collection tồn tại
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check user tồn tại
        user = await user_repo.get_user(requester_id)
        if not user:
            raise NotFoundError("User not found.")
        
        # Batch update:
        # > collections/{collection_id}/savers (sub-collection) xóa uid
        # > users/{uid}/saved_collections (array) xóa collection_id
        # > collection.saved_count giảm 1

        saver_ref = collection_repo._collection.document(collection_id).collection("savers").document(requester_id)
        saver_snapshot = await saver_ref.get()
        if not saver_snapshot.exists:
            raise AppException(status_code=400, message="Collection not saved yet.")
        
        db = collection_repo._get_db()
        batch = db.batch()
        timestamp = datetime.now(timezone.utc)
        
        collection_ref = collection_repo._collection.document(collection_id)
        user_ref = user_repo._collection.document(requester_id)
        
        # Xóa từ savers sub-collection
        saver_ref = collection_ref.collection("savers").document(requester_id)
        batch.delete(saver_ref)
        
        # Xóa collection_id từ saved_collections array của user
        batch.update(user_ref, {
            "saved_collections": fs.ArrayRemove([collection_id])
        })
        
        # Giảm saved_count
        batch.update(collection_ref, {
            "saved_count": fs.Increment(-1),
            "updated_at": timestamp
        })
        
        await batch.commit()
        return ResponseSchema(data=True)

collection_service = CollectionService()