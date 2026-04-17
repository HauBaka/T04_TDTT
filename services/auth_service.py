from repositories.user_repo import user_repo
from schemas.auth_schema import AuthResponse
from core.exceptions import NotFoundError

class AuthenticationService:
    def __init__(self, token: str) -> None:
        self.token = token
    async def doSomething(self) -> AuthResponse:
        uid = self._verify_token()
        user = await user_repo.get_user(uid)
        if not user:
            raise NotFoundError("User not found")
        # ...
        return AuthResponse(
                uid=uid, 
                username=user.get("username", ""), 
                display_name=user.get("display_name", ""), 
                email=user.get("email")
            )
    
    def _verify_token(self) -> str:
        if self.token == "valid_token":
            return "some_uid"
        else:
            raise NotFoundError("Invalid token")