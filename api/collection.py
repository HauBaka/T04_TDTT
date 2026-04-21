from fastapi import APIRouter, Depends
from schemas.collection_schema import CollectionCreateRequest, CollectionResponse, CollectionUpdateRequest
from schemas.response_schema import ResponseSchema
from services.collection_service import collection_service
from core.dependencies import get_current_user

collection_router = APIRouter()

@collection_router.post("/collections", response_model=CollectionResponse)
async def create_collection(collection_request: CollectionCreateRequest, requester=Depends(get_current_user(optional=False))):
    """Tạo một collection mới cho người dùng đã xác thực."""
    return await collection_service.create_collection(requester.get("uid"), collection_request.model_dump(exclude_none=True))

@collection_router.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: str, requester=Depends(get_current_user(optional=True))):
    """Lấy thông tin của một collection cụ thể."""
    return await collection_service.get_collection(collection_id, requester.get("uid") if requester else None)

@collection_router.patch("/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(collection_id: str, collection_request: CollectionUpdateRequest, requester=Depends(get_current_user(optional=False))):
    """Cập nhật thông tin của một collection cụ thể."""
    return await collection_service.update_collection(collection_id, requester.get("uid"), collection_request.model_dump(exclude_none=True))

@collection_router.delete("/collections/{collection_id}", response_model=ResponseSchema)
async def delete_collection(collection_id: str, requester=Depends(get_current_user(optional=False))):
    """Xóa một collection cụ thể."""
    return await collection_service.delete_collection(collection_id, requester.get("uid"))