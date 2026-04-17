from fastapi import APIRouter, HTTPException
from core.exceptions import AppException
from schemas.collection_schema import CollectionCreateRequest, CollectionPublic, CollectionResponse, CollectionUpdateRequest
from schemas.response_schema import ResponseSchema

collection_router = APIRouter()

@collection_router.post("/collections", response_model=CollectionResponse)
async def create_collection(collection_request: CollectionCreateRequest, token: str | None = None):
    """Tạo một collection mới cho người dùng đã xác thực."""
    pass

@collection_router.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: str, token: str | None = None):
    """Lấy thông tin của một collection cụ thể."""
    pass

@collection_router.patch("/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(collection_id: str, collection_request: CollectionUpdateRequest, token: str | None = None):
    """Cập nhật thông tin của một collection cụ thể."""
    pass

@collection_router.delete("/collections/{collection_id}", response_model=ResponseSchema)
async def delete_collection(collection_id: str, token: str | None = None):
    """Xóa một collection cụ thể."""
    pass