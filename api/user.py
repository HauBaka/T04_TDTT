from fastapi import APIRouter, HTTPException
from core.exceptions import AppException
from services.auth_service import AuthenticationService
from services.user_service import user_service
from schemas.user_schema import UserResponse, UserUpdateRequest
from schemas.response_schema import ResponseSchema
from test_local import BaseResponse
user_router = APIRouter()

@user_router.get("/me", response_model=ResponseSchema)
async def get_me(token: str):
    try:
        requester_uid = await user_service.auth_service.get_uid_from_token(token)
        user_dict = await user_service.user_repo.get_user(requester_uid)
 
        if not user_dict:
            return ResponseSchema(status_code=404, message="User not found", data=None)
 
        return await user_service.get_profile(token, user_dict.get("username"))
 
    except AppException as e:
        return ResponseSchema(status_code=e.status_code, message=e.message, data=None)


@user_router.get("/users/{username}", response_model=ResponseSchema)
async def get_user(username: str, token: str | None = None):
    try:
        return await user_service.get_profile(token, username)
 
    except AppException as e:
        return ResponseSchema(status_code=e.status_code, message=e.message, data=None)
@user_router.patch("/me", response_model=ResponseSchema)
async def update_user(update_data: UserUpdateRequest, token: str):
    try:
        return await user_service.update_profile(
            requester_token=token,
            update_data=update_data.model_dump(exclude_none=True)
        )

    except AppException as e:
        return ResponseSchema(status_code=e.status_code, message=e.message)


@user_router.delete("/me", response_model=ResponseSchema)
async def delete_user(token: str):
    try:
        return await user_service.delete_profile(requester_token=token)
 
    except AppException as e:
        return ResponseSchema(status_code=e.status_code, message=e.message, data=None)