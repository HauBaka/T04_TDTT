from datetime import datetime
from schemas.collection_schema import CollectionCreateRequest, CollectionPublic, CollectionUpdateRequest, CollectionResponse
from repositories.collection_repo import collection_repo
class CollectionService:
    def __init__(self, user_id: str):
        self.user_id = user_id

    async def create_collection(self, user_id: str, collection_data: dict) -> CollectionResponse:
        """Tạo một collection mới cho người dùng."""
        # collection_id = await collection_repo.create_collection(user_id, collection_data) - example
        return CollectionResponse(
                collection = CollectionPublic(
                    id = "a", 
                    owner_uid = "b", 
                    name = "c", 
                    description = "d", 
                    created_at = datetime.now(), 
                    updated_at = datetime.now())
                ) # Mock response
    
    async def get_collection(self, collection_id: str, requester_id: str | None) -> CollectionResponse:
        """Lấy thông tin của một collection cụ thể."""
        return CollectionResponse(
                collection = CollectionPublic(
                    id = "a", 
                    owner_uid = "b", 
                    name = "c", 
                    description = "d", 
                    created_at = datetime.now(), 
                    updated_at = datetime.now())
                ) # Mock response
    
    async def update_collection(self, collection_id: str, requester_id: str, update_data: dict) -> CollectionResponse:
        """Cập nhật thông tin của một collection."""
        return CollectionResponse(
                collection = CollectionPublic(
                    id = "a", 
                    owner_uid = "b", 
                    name = "c", 
                    description = "d", 
                    created_at = datetime.now(), 
                    updated_at = datetime.now())
                ) # Mock response
    