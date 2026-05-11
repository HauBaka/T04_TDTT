from fastapi import APIRouter, Depends

from core.dependencies import get_current_user
from schemas.response_schema import ResponseSchema
from schemas.user_preference_schema import UserTravelPreference
from services.user_travel_preference_service import user_travel_preference_service


user_travel_preference_router = APIRouter()


@user_travel_preference_router.get("/me/travel-preference", response_model=ResponseSchema)
async def get_my_travel_preference(current_user=Depends(get_current_user(optional=False))):
    return await user_travel_preference_service.get_my_travel_preference(
        requester_uid=current_user["uid"]
    )


@user_travel_preference_router.put("/me/travel-preference", response_model=ResponseSchema)
async def upsert_my_travel_preference(
    preference: UserTravelPreference,
    current_user=Depends(get_current_user(optional=False)),
):
    return await user_travel_preference_service.upsert_my_travel_preference(
        requester_uid=current_user["uid"],
        preference=preference,
    )


@user_travel_preference_router.delete("/me/travel-preference", response_model=ResponseSchema)
async def delete_my_travel_preference(current_user=Depends(get_current_user(optional=False))):
    return await user_travel_preference_service.delete_my_travel_preference(
        requester_uid=current_user["uid"]
    )
