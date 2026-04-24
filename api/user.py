from fastapi import APIRouter
from fastapi import Depends
from core.dependencies import get_current_user
from services.user_service import user_service
from schemas.user_schema import UserUpdateRequest
from schemas.response_schema import ResponseSchema

user_router = APIRouter()

@user_router.get("/me", response_model=ResponseSchema)
async def get_me(current_user=Depends(get_current_user(optional=False))):
    return await user_service.get_me(current_user['uid'])

@user_router.get("/users/{username}", response_model=ResponseSchema)
async def get_user(username: str, current_user=Depends(get_current_user(optional=True))):
    return await user_service.get_profile(current_user['uid'] if current_user else None, username)
    
@user_router.patch("/me", response_model=ResponseSchema)
async def update_user(update_data: UserUpdateRequest, current_user=Depends(get_current_user(optional=False))):
    return await user_service.update_profile(
        requester_uid=current_user['uid'],
        update_data=update_data.model_dump(exclude_none=True)
    )

@user_router.post("/me/liked-collection", response_model=ResponseSchema)
async def update_liked_collection(place_id: str, current_user=Depends(get_current_user(optional=False))):
    return await user_service.update_liked_collection(
        requester_uid=current_user['uid'],
        place_id=place_id,
        add=True
    )

@user_router.delete("/me/liked-collection", response_model=ResponseSchema)
async def remove_liked_collection(place_id: str, current_user=Depends(get_current_user(optional=False))):
    return await user_service.update_liked_collection(
        requester_uid=current_user['uid'],
        place_id=place_id,
        add=False
    )



@user_router.delete("/me", response_model=ResponseSchema)
async def delete_user(current_user=Depends(get_current_user(optional=False))):
    return await user_service.delete_profile(requester_uid=current_user['uid'])
