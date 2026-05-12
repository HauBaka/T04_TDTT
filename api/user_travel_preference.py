from fastapi import APIRouter, Depends

from core.dependencies import get_current_user
from schemas.response_schema import ResponseSchema
from services.user_travel_preference_service import user_travel_preference_service
from schemas.user_preference_schema import (
    UserTravelPreferenceUpdateRequest,
    UserTravelPreferenceResponse,
)


user_travel_preference_router = APIRouter()


@user_travel_preference_router.get("/me/travel-preference", response_model=ResponseSchema[UserTravelPreferenceResponse])
async def get_travel_preference(
    requester=Depends(get_current_user(optional=False)),
):
    """Lấy travel preference của current user."""
    uid = requester.get("uid")
    return await user_travel_preference_service.get_my_travel_preference(uid)


@user_travel_preference_router.put("/me/travel-preference", response_model=ResponseSchema[UserTravelPreferenceResponse])
async def update_my_travel_preference(
    preference: UserTravelPreferenceUpdateRequest,
    requester=Depends(get_current_user(optional=False)),
):
    """Tạo mới/cập nhật travel preference cho current user."""
    uid = requester.get("uid")
    return await user_travel_preference_service.update_my_travel_preference(uid, preference)


@user_travel_preference_router.delete("/me/travel-preference", response_model=ResponseSchema[bool])
async def delete_travel_preference(
    requester=Depends(get_current_user(optional=False)),
):
    """Xóa travel preference của current user."""
    uid = requester.get("uid")
    return await user_travel_preference_service.delete_my_travel_preference(uid)
