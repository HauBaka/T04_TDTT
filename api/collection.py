from fastapi import APIRouter, HTTPException
from core.exceptions import AppException
from schemas.collection_schema import CollectionCreateRequest, CollectionPublic, CollectionResponse, CollectionUpdateRequest
from schemas.response_schema import ResponseSchema
from services.collection_service import CollectionService
from services.auth_service import AuthenticationService

collection_router = APIRouter()

@collection_router.post("/collections", response_model=CollectionResponse)
async def create_collection(collection_request: CollectionCreateRequest, token: str | None = None):
    """Tạo một collection mới cho người dùng đã xác thực."""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token là bắt buộc.")
        
        auth_service = AuthenticationService(token)
        user_id = auth_service._verify_token()
        
        service = CollectionService()
        return await service.create_collection(user_id, collection_request.model_dump(exclude_none=True))
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@collection_router.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: str, token: str | None = None):
    """Lấy thông tin của một collection cụ thể."""
    try:
        auth_service = AuthenticationService(token) if token else None
        requester_id = await auth_service._verify_token() if auth_service else None

        service = CollectionService()
        return await service.get_collection(collection_id, requester_id)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@collection_router.patch("/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(collection_id: str, collection_request: CollectionUpdateRequest, token: str | None = None):
    """Cập nhật thông tin của một collection cụ thể."""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token là bắt buộc.")
        
        auth_service = AuthenticationService(token)
        requester_id = await auth_service._verify_token()

        service = CollectionService()
        return await service.update_collection(collection_id, requester_id, collection_request.model_dump(exclude_none=True))
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@collection_router.delete("/collections/{collection_id}", response_model=ResponseSchema)
async def delete_collection(collection_id: str, token: str | None = None):
    """Xóa một collection cụ thể."""
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Token là bắt buộc.")

        auth_service = AuthenticationService(token)
        requester_id = await auth_service._verify_token()

        service = CollectionService()
        deleted = await service.delete_collection(collection_id, requester_id)
        if not deleted:
            raise AppException("Xóa collection thất bại.")
        return ResponseSchema(message="xóa collection thành công.")
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)