from datetime import datetime, timezone
from schemas.collection_schema import CollectionCreateRequest, CollectionPublic, CollectionUpdateRequest, CollectionResponse
from repositories.collection_repo import collection_repo
from core.exceptions import AppException, NotFoundError, ValidationError
class CollectionService:
    def __init__(self, user_id: str | None = None):
        self.user_id = user_id

    async def create_collection(self, user_id: str, collection_data: dict) -> CollectionResponse:
        """Tạo một collection mới cho người dùng."""
        # collection_id = await collection_repo.create_collection(user_id, collection_data) - example
        if not str(collection_data.get("name", "")).strip():
            raise ValidationError("Tên collection không được để trống.")
        
        request = CollectionCreateRequest.model_validate(collection_data)
        data = request.model_dump(exclude_none=True)
        created_collection = await collection_repo.create_collection(user_id, data)
        if not created_collection:
            raise AppException("Không thể tạo collection.")
        
        return self.build_response(created_collection)
    
    async def get_collection(self, collection_id: str, requester_id: str | None) -> CollectionResponse:
        """Lấy thông tin của một collection cụ thể."""
        existing_collection = await collection_repo.get_collection(collection_id)
        if not existing_collection:
            raise NotFoundError("Collection không tồn tại.")
        
        visibility = existing_collection.get("visibility", "public")
        owner_uid = existing_collection.get("owner_uid", "")
        collaborators = existing_collection.get("collaborators", [])

        if visibility == "private":
            if requester_id != owner_uid and requester_id not in collaborators:
                raise AppException("Bạn không có quyền truy cập collection này.", status_code=403)
        
        return self.build_response(existing_collection)
    
    async def update_collection(self, collection_id: str, requester_id: str, update_data: dict) -> CollectionResponse:
        """Cập nhật thông tin của một collection."""
        existing_collection = await collection_repo.get_collection(collection_id)
        if not existing_collection:
            raise NotFoundError("Collection không tồn tại.")
        
        owner_uid = existing_collection.get("owner_uid", "")
        collaberators = existing_collection.get("collaborators", [])
        if requester_id != owner_uid and requester_id not in collaberators:
            raise AppException("Bạn không có quyền chỉnh sửa collection này.", status_code=403)
        
        if existing_collection.get("name") == "liked":
            if "name" in update_data and str(update_data["name"]).strip() != "liked":
                raise AppException("Không thể đổi tên collection mặc định 'liked'.", status_code=403)

        request = CollectionUpdateRequest.model_validate(update_data)
        data = request.model_dump(exclude_none=True)
        if not data:
            raise ValidationError("Dữ liệu cập nhật không hợp lệ.")
        
        updated_data = await collection_repo.update_collection(requester_id, collection_id, data)
        if not updated_data:
            raise AppException("Cập nhật collection thất bại.", status_code=500)
        
        return self.build_response(updated_data)
        
    async def delete_collection(self, collection_id: str, requester_id: str) -> bool:
        """Xóa một collection."""
        existing_collection = await collection_repo.get_collection(collection_id)
        if not existing_collection:
            raise NotFoundError("Collection không tồn tại.")
        
        owner_uid = existing_collection.get("owner_uid", "")
        if requester_id != owner_uid:
            raise AppException("Bạn không có quyền xóa collection này.", status_code=403)
        
        if existing_collection.get("name") == "liked":
            raise AppException("Không thể xóa collection mặc định 'liked'.", status_code=403)
        
        return await collection_repo.delete_collection(requester_id, collection_id)
    
    def build_response(self, collection_data: dict) -> CollectionResponse:
        """Xây dựng response cho collection."""
        if not collection_data:
            raise NotFoundError("Collection không tồn tại.")
        
        collection = CollectionPublic(
            id = collection_data.get("id", ""),
            owner_uid = collection_data.get("owner_uid", ""),
            name = collection_data.get("name", ""),
            description = collection_data.get("description", ""),
            created_at = collection_data.get("created_at", datetime.now(timezone.utc)),
            updated_at = collection_data.get("updated_at", datetime.now(timezone.utc)),
            collaborators = collection_data.get("collaborators", []),
            places = collection_data.get("places", []),
            tags = collection_data.get("tags", []),
            visibility = collection_data.get("visibility", "public")
        )
        return CollectionResponse(collection=collection)