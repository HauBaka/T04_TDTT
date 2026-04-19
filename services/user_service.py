from core.exceptions import NotFoundError
from repositories.user_repo import UserRepository
from services.auth_service import AuthenticationService
from schemas.user_schema import UserResponse, UserPublic, UserPrivate
from schemas.response_schema import ResponseSchema
class UserService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.auth_service = AuthenticationService()
    async def get_profile(self, requester_token: str | None, target_username: str) -> Res:
        target_user_dict = await self.user_repo.get_user_by_username(target_username)
        if not target_user_dict:
            raise NotFoundError("User not found")
 
        requester_uid = None
        if requester_token:
            requester_uid = await self.auth_service.get_uid_from_token(requester_token)
 
        is_owner = requester_uid == target_user_dict.get("uid")
        user_data = UserPrivate(**target_user_dict) if is_owner else UserPublic(**target_user_dict)
 
        return ResponseSchema(status_code=200, message="Success", data=user_data)    
    async def update_profile(self, requester_token: str, update_data: dict) -> UserResponse:
        requester_uid = await self.auth_service.get_uid_from_token(requester_token)
        #lọc bỏ các field None để không ghi đè dữ liệu cũ
        filtered_data = {k: v for k, v in update_data.items() if v is not None}
        if filtered_data:
            await self.user_repo.update_user(requester_uid, filtered_data)
 
        updated_user_dict = await self.user_repo.get_user(requester_uid)
        return ResponseSchema(status_code=200, message="Profile updated successfully", data=UserPrivate(**updated_user_dict)) # Mock response    
    async def delete_profile(self, requester_token: str) -> bool:
        requester_uid = await self.auth_service.get_uid_from_token(requester_token)
        await self.user_repo.delete_user(requester_uid)
        return ResponseSchema(status_code=200, message="Account deleted successfully", data=None) #mock response
        
user_service = UserService()