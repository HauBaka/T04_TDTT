from fastapi import APIRouter, Depends

from core.dependencies import get_current_user
from schemas.response_schema import ResponseSchema
from services.user_travel_preference_service import user_travel_preference_service
from schemas.user_preference_schema import (
    UserTravelPreferenceUpsertRequest,
    UserTravelPreferenceResponse,
)


user_travel_preference_router = APIRouter()


@user_travel_preference_router.get("/travel-preference/{uid}", response_model=ResponseSchema[UserTravelPreferenceResponse])
async def get_travel_preference(
    uid: str,
    requester=Depends(get_current_user(optional=True)),
):
    """Lấy travel preference của một user."""
    return await user_travel_preference_service.get_my_travel_preference(uid)


@user_travel_preference_router.put("/travel-preference/{uid}", response_model=ResponseSchema[UserTravelPreferenceResponse])
async def upsert_my_travel_preference(
    uid: str,
    preference: UserTravelPreferenceUpsertRequest,
):
    """Tạo mới/cập nhật travel preference."""
    return await user_travel_preference_service.upsert_my_travel_preference(uid, preference)


@user_travel_preference_router.delete("/travel-preference/{uid}", response_model=ResponseSchema[bool])
async def delete_travel_preference(
    uid: str,
    requester=Depends(get_current_user(optional=False)),
):
    """Xóa travel preference của một user."""
    return await user_travel_preference_service.delete_my_travel_preference(uid)
