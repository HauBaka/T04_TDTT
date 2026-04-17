from core.exceptions import NotFoundError
from repositories.user_repo import UserRepository
from services.auth_service import AuthenticationService
from schemas.user_schema import UserResponse, UserPublic, UserPrivate

class UserService:
    def __init__(self):
        self.user_repo = UserRepository()
    
    async def get_profile(self, requester_token: str | None, target_username: str) -> UserResponse:
        return UserResponse(user=UserPublic(username=target_username, display_name=target_username)) # Mock response

    
    async def update_profile(self, requester_token: str, update_data: dict) -> UserResponse:
        return UserResponse(user=UserPrivate(username="mock_user", display_name="Mock User", email=None)) # Mock response
    
    async def delete_profile(self, requester_token: str) -> bool:
        return True # Mock response

        
user_service = UserService()
