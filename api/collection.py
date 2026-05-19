from fastapi import APIRouter, BackgroundTasks, Depends
from schemas.collection_schema import (
    AddMultipleContributorsRequest, 
    AddMultiplePlacesRequest, 
    AddMultipleTagsRequest,  
    CollectionUpdateRequest, 
    RemoveMultipleContributorsRequest, 
    RemoveMultiplePlacesRequest, 
    RemoveMultipleTagsRequest,
    CollectionCreateRequest, 
    CollectionContributorResponse, 
    CollectionPlaceResponse, 
    CollectionResponse, 
    CollectionSaverResponse,
)
from schemas.response_schema import ResponseSchema
from services.collection_service import collection_service
from core.dependencies import get_current_user

collection_router = APIRouter()

# Collection

@collection_router.post("/collections", response_model=ResponseSchema[CollectionResponse])
async def create_collection(collection_request: CollectionCreateRequest, requester=Depends(get_current_user(optional=False))):
    """Tạo một collection mới cho người dùng đã xác thực."""
    return await collection_service.create_collection(requester.get("uid"), collection_request)

@collection_router.get("/collections/{collection_id}", response_model=ResponseSchema[CollectionResponse])
async def get_collection(collection_id: str, requester=Depends(get_current_user(optional=True))):
    """Lấy thông tin của một collection cụ thể."""
    return await collection_service.get_collection(collection_id, requester.get("uid") if requester else None)

@collection_router.patch("/collections/{collection_id}", response_model=ResponseSchema[CollectionResponse])
async def update_collection(collection_id: str, collection_request: CollectionUpdateRequest, requester=Depends(get_current_user(optional=False))):
    """Cập nhật thông tin của một collection cụ thể."""
    return await collection_service.update_collection(collection_id, requester.get("uid"), collection_request)

@collection_router.delete("/collections/{collection_id}", response_model=ResponseSchema[bool])
async def delete_collection(collection_id: str, background_tasks: BackgroundTasks, requester=Depends(get_current_user(optional=False))):
    """Xóa một collection cụ thể."""
    return await collection_service.delete_collection(collection_id, requester.get("uid"), background_tasks=background_tasks)

# Place

@collection_router.post("/collections/{collection_id}/places", response_model=ResponseSchema[CollectionResponse])
async def add_places_to_collection(collection_id: str, places_request: AddMultiplePlacesRequest, background_tasks: BackgroundTasks, requester=Depends(get_current_user(optional=False))):
    """Thêm nhiều địa điểm vào một collection cụ thể."""
    return await collection_service.add_places_to_collection(collection_id, requester.get("uid"), places_request.place_ids, background_tasks=background_tasks)

@collection_router.get("/collections/{collection_id}/places", response_model=ResponseSchema[list[CollectionPlaceResponse]])
async def get_places_from_collection(collection_id: str, requester=Depends(get_current_user(optional=True))):
    """Lấy danh sách chi tiết địa điểm từ một collection cụ thể."""
    return await collection_service.get_places_from_collection(collection_id, requester.get("uid") if requester else None)

@collection_router.delete("/collections/{collection_id}/places", response_model=ResponseSchema[CollectionResponse])
async def remove_places_from_collection(collection_id: str, places_request: RemoveMultiplePlacesRequest, background_tasks: BackgroundTasks, requester=Depends(get_current_user(optional=False))):
    """Xóa nhiều địa điểm khỏi một collection cụ thể."""
    return await collection_service.remove_places_from_collection(collection_id, requester.get("uid"), places_request.place_ids, background_tasks=background_tasks)

# Contributor

@collection_router.post("/collections/{collection_id}/contributors", response_model=ResponseSchema[CollectionResponse])
async def add_contributors_to_collection(collection_id: str, contributors_request: AddMultipleContributorsRequest, requester=Depends(get_current_user(optional=False))):
    """Thêm nhiều cộng tác viên vào một collection cụ thể."""
    return await collection_service.add_contributors_to_collection(collection_id, requester.get("uid"), contributors_request.contributor_uids)

@collection_router.get("/collections/{collection_id}/contributors", response_model=ResponseSchema[list[CollectionContributorResponse]])
async def get_contributors_from_collection(collection_id: str, requester=Depends(get_current_user(optional=True))):
    """Lấy danh sách chi tiết cộng tác viên từ một collection cụ thể."""
    return await collection_service.get_contributors_from_collection(collection_id, requester.get("uid") if requester else None)

@collection_router.delete("/collections/{collection_id}/contributors", response_model=ResponseSchema[CollectionResponse])
async def remove_contributors_from_collection(collection_id: str, contributors_request: RemoveMultipleContributorsRequest, requester=Depends(get_current_user(optional=False))):
    """Xóa nhiều cộng tác viên khỏi một collection cụ thể."""
    return await collection_service.remove_contributors_from_collection(collection_id, requester.get("uid"), contributors_request.contributor_uids)

# Tag

@collection_router.post("/collections/{collection_id}/tags", response_model=ResponseSchema[CollectionResponse])
async def add_tags_to_collection(collection_id: str, tags_request: AddMultipleTagsRequest, requester=Depends(get_current_user(optional=False))):
    """Thêm nhiều tag vào một collection cụ thể."""
    return await collection_service.add_tags_to_collection(collection_id, requester.get("uid"), tags_request.tags)

@collection_router.delete("/collections/{collection_id}/tags", response_model=ResponseSchema[CollectionResponse])
async def remove_tags_from_collection(collection_id: str, tags_request: RemoveMultipleTagsRequest, requester=Depends(get_current_user(optional=False))):
    """Xóa nhiều tag khỏi một collection cụ thể."""
    return await collection_service.remove_tags_from_collection(collection_id, requester.get("uid"), tags_request.tags)

# Savers

@collection_router.get("/collections/{collection_id}/savers", response_model=ResponseSchema[list[CollectionSaverResponse]])
async def get_savers_from_collection(collection_id: str, requester=Depends(get_current_user(optional=True))):
    """Lấy danh sách chi tiết người dùng đã lưu một collection cụ thể."""
    return await collection_service.get_savers_from_collection(collection_id, requester.get("uid") if requester else None)
