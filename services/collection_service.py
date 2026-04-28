from datetime import datetime, timezone
from repositories.user_repo import user_repo
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
        
        return self.build_response(created_collection)
    
    async def get_collection(self, collection_id: str, requester_id: str | None) -> ResponseSchema[CollectionResponse]:
        """Lấy thông tin của một collection cụ thể."""
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        visibility = CollectionVisibility(collection.get("visibility", CollectionVisibility.PUBLIC.value))
        owner_uid = collection.get("owner_uid", "")
        collaborators = collection.get("collaborators", [])

        if visibility == CollectionVisibility.PRIVATE:
            collaborator_uids = [
                c.get("uid") for c in collaborators 
                if isinstance(c, dict) and "uid" in c
            ]

            if requester_id != owner_uid and requester_id not in collaborator_uids:
                raise AppException(status_code=403, message="You do not have permission to view this collection.")
        
        return self.build_response(collection)
    
    async def update_collection(self, collection_id: str, requester_id: str, update_data: dict) -> ResponseSchema[CollectionResponse]:
        """Cập nhật thông tin của một collection."""

        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check requester 
        requester = await user_repo.get_user(requester_id)
        if not requester:
            raise NotFoundError("User not found.")

        owner_uid = collection.get("owner_uid", "")
        collaborators = collection.get("collaborators", [])
        collaborators_ids = [c.get("uid") for c in collaborators if isinstance(c, dict) and "uid" in c]

        if requester_id != owner_uid and requester_id not in collaborators_ids:
            raise AppException(status_code=403, message="You do not have permission to edit this collection.")

        # So sánh với default liked collection
        if collection.get("id") == requester.get("liked_collection", ""):
            if "name" in update_data and str(update_data["name"]).strip().lower() != "liked":
                raise AppException(status_code=403, message="Cannot change the name of the default collection.")
        
        updated_data = await collection_repo.update_collection(collection_id, update_data)
        if not updated_data:
            raise AppException(status_code=500, message="Failed to update collection.")
        
        return self.build_response(updated_data)
        
    async def add_places_to_collection(self, collection_id: str, requester_id: str, place_ids: list[str]) -> ResponseSchema[CollectionResponse]:
        """Thêm nhiều địa điểm vào một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check quyền
        owner_uid = collection.get("owner_uid", "")
        collaborators = collection.get("collaborators", [])
        collaborators_ids = [c.get("uid") for c in collaborators if isinstance(c, dict) and "uid" in c]
        
        if requester_id != owner_uid and requester_id not in collaborators_ids:
            raise AppException(status_code=403, message="You do not have permission to edit this collection.")
        
        # Tạo place objects
        timestamp = datetime.now(timezone.utc)
        places_to_add = [
            CollectionPlace(
                place_id=place_id,
                added_at=timestamp,
                added_by=requester_id
            ).model_dump() for place_id in place_ids
        ]
        
        # Thêm vào collection
        updated_collection = await collection_repo.add_places_to_collection(collection_id, places_to_add)
        if not updated_collection:
            raise AppException(status_code=500, message="Failed to add places to collection.")
        
        return self.build_response(updated_collection)

    async def remove_places_from_collection(self, collection_id: str, requester_id: str, place_ids: list[str]) -> ResponseSchema[CollectionResponse]:
        """Xóa nhiều địa điểm khỏi một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check quyền
        owner_uid = collection.get("owner_uid", "")
        collaborators = collection.get("collaborators", [])
        collaborators_ids = [c.get("uid") for c in collaborators if isinstance(c, dict) and "uid" in c]
        
        if requester_id != owner_uid and requester_id not in collaborators_ids:
            raise AppException(status_code=403, message="You do not have permission to edit this collection.")
        
        # Xóa từ collection
        updated_collection = await collection_repo.remove_places_from_collection(collection_id, place_ids)
        if not updated_collection:
            raise AppException(status_code=500, message="Failed to remove places from collection.")
        
        return self.build_response(updated_collection)
    
    async def add_collaborators_to_collection(self, collection_id: str, requester_id: str, collaborator_uids: list[str]) -> ResponseSchema[CollectionResponse]:
        """Thêm nhiều cộng tác viên vào một collection. Gửi invitation"""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check quyền - chỉ owner mới có thể thêm collaborators
        owner_uid = collection.get("owner_uid", "")
        if requester_id != owner_uid:
            raise AppException(status_code=403, message="You do not have permission to add collaborators to this collection.")
        
        # Lấy thông tin người dùng để tạo collaborator objects
        timestamp = datetime.now(timezone.utc)
        collaborators_to_add = []
        
        for uid in collaborator_uids:
            user = await user_repo.get_user(uid)
            if not user:
                raise NotFoundError(f"User {uid} not found.")
            
            collaborator = CollectionCollaborator(
                uid=uid,
                display_name=user.get("display_name", ""),
                username=user.get("username", ""),
                avatar_url=user.get("avatar_url", None),
                contributed_count=0,
                joined_at=timestamp
            )
            collaborators_to_add.append(collaborator.model_dump())
        
        # Thêm vào collection
        updated_collection = await collection_repo.add_collaborators_to_collection(collection_id, collaborators_to_add)
        if not updated_collection:
            raise AppException(status_code=500, message="Failed to add collaborators to collection.")
        
        return self.build_response(updated_collection)
    
    async def remove_collaborators_from_collection(self, collection_id: str, requester_id: str, collaborator_uids: list[str]) -> ResponseSchema[CollectionResponse]:
        """Xóa nhiều cộng tác viên khỏi một collection. Gửi notification"""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check quyền - chỉ owner mới có thể xóa collaborators
        owner_uid = collection.get("owner_uid", "")
        if requester_id != owner_uid:
            raise AppException(status_code=403, message="You do not have permission to remove collaborators from this collection.")
        
        # Xóa từ collection
        updated_collection = await collection_repo.remove_collaborators_from_collection(collection_id, collaborator_uids)
        if not updated_collection:
            raise AppException(status_code=500, message="Failed to remove collaborators from collection.")
        
        return self.build_response(updated_collection)
    
    async def add_tags_to_collection(self, collection_id: str, requester_id: str, tags: list[str]) -> ResponseSchema[CollectionResponse]:
        """Thêm nhiều tag vào một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check quyền
        owner_uid = collection.get("owner_uid", "")
        collaborators = collection.get("collaborators", [])
        collaborators_ids = [c.get("uid") for c in collaborators if isinstance(c, dict) and "uid" in c]
        
        if requester_id != owner_uid and requester_id not in collaborators_ids:
            raise AppException(status_code=403, message="You do not have permission to edit this collection.")
        
        # Thêm tags
        updated_collection = await collection_repo.add_tags_to_collection(collection_id, tags)
        if not updated_collection:
            raise AppException(status_code=500, message="Failed to add tags to collection.")
        
        return self.build_response(updated_collection)

    async def remove_tags_from_collection(self, collection_id: str, requester_id: str, tags: list[str]) -> ResponseSchema[CollectionResponse]:
        """Xóa nhiều tag khỏi một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        # Check quyền
        owner_uid = collection.get("owner_uid", "")
        collaborators = collection.get("collaborators", [])
        collaborators_ids = [c.get("uid") for c in collaborators if isinstance(c, dict) and "uid" in c]
        
        if requester_id != owner_uid and requester_id not in collaborators_ids:
            raise AppException(status_code=403, message="You do not have permission to edit this collection.")
        
        # Xóa tags
        updated_collection = await collection_repo.remove_tags_from_collection(collection_id, tags)
        if not updated_collection:
            raise AppException(status_code=500, message="Failed to remove tags from collection.")
        
        return self.build_response(updated_collection)

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
    
    def build_response(self, collection_data: dict) -> ResponseSchema[CollectionResponse]:
        """Xây dựng response cho collection."""
        if not collection_data:
            raise NotFoundError("Invalid collection ID.")
        
        collection = CollectionPublic(
            id = collection_data.get("id", ""),
            owner_uid = collection_data.get("owner_uid", ""),
            name = collection_data.get("name", ""),
            description = collection_data.get("description", ""),
            thumbnail_url = collection_data.get("thumbnail_url", None),
            created_at = collection_data.get("created_at", datetime.now(timezone.utc)),
            updated_at = collection_data.get("updated_at", datetime.now(timezone.utc)),
            collaborators = collection_data.get("collaborators", []),
            places = collection_data.get("places", []),
            tags = collection_data.get("tags", []),
            visibility = CollectionVisibility(collection_data.get("visibility", "public"))
        )
        return ResponseSchema(data=CollectionResponse(collection=collection))

collection_service = CollectionService()