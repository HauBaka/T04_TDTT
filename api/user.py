from fastapi import APIRouter, HTTPException
from core.exceptions import AppException
from services.auth_service import AuthenticationService
from schemas.user_schema import UserResponse, UserUpdateRequest

user_router = APIRouter()

@user_router.get("/me", response_model=UserResponse)
async def get_me(token: str):
    pass

@user_router.get("/users/{username}", response_model=UserResponse)
async def get_user(username: str, token: str | None = None):
    try:
        pass
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@user_router.patch("/me", response_model=UserResponse)
async def update_user(update_data: UserUpdateRequest, token: str):
    pass

@user_router.delete("/me")
async def delete_user(token: str):
    pass