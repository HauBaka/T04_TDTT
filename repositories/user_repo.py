from core.database import get_db

class UserRepository:
    def __init__(self):
        self.user_collection = "users"

    def _get_db(self):
        return get_db()
    
    async def get_user(self, uid: str) -> dict | None:
        pass
    async def create_user(self, user_data: dict) -> str | None:
        pass
        
    async def update_user(self, uid: str, update_data: dict) -> bool | None:
        pass

    async def delete_user(self, uid: str) -> bool | None:
        pass

    async def get_user_by_username(self, username: str) -> dict | None:
        pass

user_repo = UserRepository()