from fastapi import APIRouter
from core.exceptions import AppException
from firebase_admin import auth
from services.user_service import user_service
from schemas.user_schema import UserUpdateRequest
from schemas.response_schema import ResponseSchema

user_router = APIRouter()

class AuthService:
    async def get_uid_from_token(self, token: str) -> str:
        try:
            decoded_info = auth.verify_id_token(token)
            uid = decoded_info["uid"]
            return uid
        except auth.ExpiredIdTokenError:
            raise AppException(status_code=401, message="Token đã hết hạn")
        except auth.InvalidIdTokenError:
            raise AppException(status_code=401, message="Token không hợp lệ")
        except Exception as e:
            raise AppException(status_code=401, message=f"Xác thực thất bại: {str(e)}")
            
@user_router.get("/me", response_model=ResponseSchema)
async def get_me(token: str):
    try:
        return await user_service.get_me(token)
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
