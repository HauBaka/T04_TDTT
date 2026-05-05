from fastapi import APIRouter, Depends
from schemas.collection_schema import AddMultipleCollaboratorsRequest, AddMultiplePlacesRequest, AddMultipleTagsRequest, CollectionCreateRequest, CollectionResponse, CollectionUpdateRequest, RemoveMultipleCollaboratorsRequest, RemoveMultiplePlacesRequest, RemoveMultipleTagsRequest
from schemas.response_schema import ResponseSchema
from services.collection_service import collection_service
from core.dependencies import get_current_user

collection_router = APIRouter()

@collection_router.post("/collections", response_model=ResponseSchema[CollectionResponse])
async def create_collection(collection_request: CollectionCreateRequest, requester=Depends(get_current_user(optional=False))):
    """Tạo một collection mới cho người dùng đã xác thực."""
    return await collection_service.create_collection(requester.get("uid"), collection_request.model_dump(exclude_none=True))

@collection_router.get("/collections/{collection_id}", response_model=ResponseSchema[CollectionResponse])
async def get_collection(collection_id: str, requester=Depends(get_current_user(optional=True))):
    """Lấy thông tin của một collection cụ thể."""
    return await collection_service.get_collection(collection_id, requester.get("uid") if requester else None)

@collection_router.patch("/collections/{collection_id}", response_model=ResponseSchema[CollectionResponse])
async def update_collection(collection_id: str, collection_request: CollectionUpdateRequest, requester=Depends(get_current_user(optional=False))):
    """Cập nhật thông tin của một collection cụ thể."""
    return await collection_service.update_collection(collection_id, requester.get("uid"), collection_request.model_dump(exclude_none=True))

@collection_router.post("/collections/{collection_id}/places", response_model=ResponseSchema[CollectionResponse])
async def add_places_to_collection(collection_id: str, places_request: AddMultiplePlacesRequest, requester=Depends(get_current_user(optional=False))):
    """Thêm nhiều địa điểm vào một collection cụ thể."""
    return await collection_service.add_places_to_collection(collection_id, requester.get("uid"), places_request.place_ids)

@collection_router.post("/collections/{collection_id}/collaborators", response_model=ResponseSchema[CollectionResponse])
async def add_collaborators_to_collection(collection_id: str, collaborators_request: AddMultipleCollaboratorsRequest, requester=Depends(get_current_user(optional=False))):
    """Thêm nhiều cộng tác viên vào một collection cụ thể."""
    return await collection_service.add_collaborators_to_collection(collection_id, requester.get("uid"), collaborators_request.collaborator_uids)

@collection_router.post("/collections/{collection_id}/tags", response_model=ResponseSchema[CollectionResponse])
async def add_tags_to_collection(collection_id: str, tags_request: AddMultipleTagsRequest, requester=Depends(get_current_user(optional=False))):
    """Thêm nhiều tag vào một collection cụ thể."""
    return await collection_service.add_tags_to_collection(collection_id, requester.get("uid"), tags_request.tags)

@collection_router.delete("/collections/{collection_id}/places", response_model=ResponseSchema[CollectionResponse])
async def remove_places_from_collection(collection_id: str, places_request: RemoveMultiplePlacesRequest, requester=Depends(get_current_user(optional=False))):
    """Xóa nhiều địa điểm khỏi một collection cụ thể."""
    return await collection_service.remove_places_from_collection(collection_id, requester.get("uid"), places_request.place_ids)

@collection_router.delete("/collections/{collection_id}/collaborators", response_model=ResponseSchema[CollectionResponse])
async def remove_collaborators_from_collection(collection_id: str, collaborators_request: RemoveMultipleCollaboratorsRequest, requester=Depends(get_current_user(optional=False))):
    """Xóa nhiều cộng tác viên khỏi một collection cụ thể."""
    return await collection_service.remove_collaborators_from_collection(collection_id, requester.get("uid"), collaborators_request.collaborator_uids)

@collection_router.delete("/collections/{collection_id}/tags", response_model=ResponseSchema[CollectionResponse])
async def remove_tags_from_collection(collection_id: str, tags_request: RemoveMultipleTagsRequest, requester=Depends(get_current_user(optional=False))):
    """Xóa nhiều tag khỏi một collection cụ thể."""
    return await collection_service.remove_tags_from_collection(collection_id, requester.get("uid"), tags_request.tags)

@collection_router.delete("/collections/{collection_id}", response_model=ResponseSchema[bool])
async def delete_collection(collection_id: str, requester=Depends(get_current_user(optional=False))):
    """Xóa một collection cụ thể."""
    return await collection_service.delete_collection(collection_id, requester.get("uid"))

@collection_router.post("/collections/{collection_id}/save", response_model=ResponseSchema[bool])
async def save_collection(collection_id: str, requester=Depends(get_current_user(optional=False))):
    """Lưu một collection vào danh sách đã lưu của người dùng."""
    return await collection_service.save_collection(collection_id, requester.get("uid"))

@collection_router.post("/collections/{collection_id}/unsave", response_model=ResponseSchema[bool])
async def unsave_collection(collection_id: str, requester=Depends(get_current_user(optional=False))):
    """Bỏ lưu một collection khỏi danh sách đã lưu của người dùng."""
    return await collection_service.unsave_collection(collection_id, requester.get("uid"))

