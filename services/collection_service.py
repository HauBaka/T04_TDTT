from datetime import datetime, timezone
from repositories.user_repo import user_repo
from schemas.collection_schema import CollectionPublic, CollectionResponse, CollectionVisibility
from repositories.collection_repo import collection_repo
from core.exceptions import AppException, NotFoundError
class CollectionService:
    def __init__(self):
        self.collection_repo = collection_repo

    async def create_collection(self, user_id: str, collection_data: dict) -> CollectionResponse:
        """Tạo một collection mới cho người dùng."""
        created_collection = await collection_repo.create_collection(user_id, collection_data)
        
        if not created_collection:
            raise AppException(status_code=500, message="Failed to create collection.")
        
        return self.build_response(created_collection)
    
    async def get_collection(self, collection_id: str, requester_id: str | None) -> CollectionResponse:
        """Lấy thông tin của một collection cụ thể."""
        collection = await collection_repo.get_collection(collection_id)
        if not collection:
            raise NotFoundError("Invalid collection ID.")
        
        visibility = collection.get("visibility", CollectionVisibility.PUBLIC)
        owner_uid = collection.get("owner_uid", "")
        collaborators = collection.get("collaborators", [])

        if visibility == CollectionVisibility.PRIVATE:
            if requester_id != owner_uid and requester_id not in collaborators:
                raise AppException(status_code=403, message="You do not have permission to view this collection.")
        
        return self.build_response(collection)
    
    async def update_collection(self, collection_id: str, requester_id: str, update_data: dict) -> CollectionResponse:
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
        
    async def delete_collection(self, collection_id: str, requester_id: str) -> bool:
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
        
        return await collection_repo.delete_collection(collection_id)
    
    def build_response(self, collection_data: dict) -> CollectionResponse:
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
        return CollectionResponse(collection=collection)
    
collection_service = CollectionService()