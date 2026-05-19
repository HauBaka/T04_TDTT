from fastapi import APIRouter, BackgroundTasks
from fastapi import Depends
from fastapi import APIRouter, Depends

from core.dependencies import get_current_user
from schemas.collection_schema import (
    CollectionPlaceResponse,
    CollectionPrivateResponse,
    CollectionPublicResponse,
)
from schemas.conversation_schema import ConversationResponse
from schemas.response_schema import ResponseSchema, UserPreviewResponse
from schemas.user_schema import (
    AddFavouritePlaceRequest,
    UserPrivateResponse,
    UserPublicResponse,
    UserSaveCollectionRequest,
    UserUpdateRequest,
)
from services.user_service import user_service

user_router = APIRouter()


@user_router.get("/me", response_model=ResponseSchema[UserPrivateResponse])
async def get_me(current_user=Depends(get_current_user(optional=False))):
    """Lấy thông tin hồ sơ của người dùng hiện tại."""
    return await user_service.get_me(current_user["uid"])


@user_router.get(
    "/users/{username}",
    response_model=ResponseSchema[UserPublicResponse | UserPrivateResponse],
)
async def get_user(
    username: str, current_user=Depends(get_current_user(optional=True))
):
    """Lấy thông tin hồ sơ của một user cụ thể theo username. Nếu requester đã xác thực và là chủ sở hữu của profile thì trả về thông tin private, ngược lại trả về public."""
    return await user_service.get_profile(
        current_user["uid"] if current_user else None, username
    )


@user_router.get("/users", response_model=ResponseSchema[list[UserPreviewResponse]])
async def suggest_users(
    search: str, current_user=Depends(get_current_user(optional=True))
):
    """Gợi ý người dùng dựa trên chuỗi truy vấn. Trả về danh sách người dùng có username hoặc display_name khớp với truy vấn."""
    return await user_service.suggest_users(query=search)


@user_router.patch("/me", response_model=ResponseSchema[UserPrivateResponse])
async def update_user(
    update_data: UserUpdateRequest,
    current_user=Depends(get_current_user(optional=False)),
):
    """Cập nhật thông tin hồ sơ của người dùng hiện tại."""
    return await user_service.update_profile(
        requester_uid=current_user["uid"], update_data=update_data
    )


# --- QUẢN LÝ BỘ SƯU TẬP (COLLECTIONS) ---


@user_router.get(
    "/me/my-collections", response_model=ResponseSchema[list[CollectionPrivateResponse]]
)
async def get_my_collections(current_user=Depends(get_current_user(optional=False))):
    """Lấy danh sách các collection mà người dùng đã tạo."""
    return await user_service.get_owned_collections(requester_uid=current_user["uid"])


@user_router.get(
    "/me/contributing-collections",
    response_model=ResponseSchema[list[CollectionPrivateResponse]],
)
async def get_contributing_collections(
    current_user=Depends(get_current_user(optional=False)),
):
    """Lấy danh sách các collection mà người dùng đang cộng tác."""
    return await user_service.get_contributing_collections(
        requester_uid=current_user["uid"]
    )


@user_router.get(
    "/me/saved-collections",
    response_model=ResponseSchema[list[CollectionPublicResponse]],
)
async def get_saved_collections(current_user=Depends(get_current_user(optional=False))):
    """Lấy danh sách các collection mà người dùng đã lưu."""
    return await user_service.get_saved_collections(requester_uid=current_user["uid"])


@user_router.post("/me/saved-collections", response_model=ResponseSchema[bool])
async def save_collection(collection: UserSaveCollectionRequest, background_tasks: BackgroundTasks, current_user=Depends(get_current_user(optional=False))):
    """Lưu một collection vào danh sách đã lưu của người dùng."""
    return await user_service.save_collection(requester_uid=current_user['uid'], collection=collection, background_tasks=background_tasks)

@user_router.delete("/me/saved-collections/{collection_id}", response_model=ResponseSchema[bool])
async def unsave_collection(collection_id: str, background_tasks: BackgroundTasks, current_user=Depends(get_current_user(optional=False))):
    """Xóa một collection khỏi danh sách đã lưu của người dùng."""
    return await user_service.unsave_collection(requester_uid=current_user['uid'], collection_id=collection_id, background_tasks=background_tasks)

# --- conversations
@user_router.get(
    "/me/conversations", response_model=ResponseSchema[list[ConversationResponse]]
)
async def get_conversations(current_user=Depends(get_current_user(optional=False))):
    """Lấy danh sách các cuộc trò chuyện mà người dùng đã tham gia."""
    return await user_service.get_conversations(requester_uid=current_user["uid"])


@user_router.delete("/me", response_model=ResponseSchema)
async def delete_user(current_user=Depends(get_current_user(optional=False))):
    """Xóa tài khoản người dùng hiện tại."""
    return await user_service.delete_profile(requester_uid=current_user["uid"])
