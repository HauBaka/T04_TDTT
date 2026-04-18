from core.database import get_db

class UserRepository:
    def __init__(self):
        self.user_collection = "users"

    def _get_db(self):
        return get_db()
    
    async def get_user(self, uid: str) -> dict | None:
        pass
    async def create_user(self, user_data: dict) -> bool:
        # [Nhánh Not Exists]: Lưu thông tin user mới
        db = self._get_db()
        uid = user_data.get("uid")

        if not uid:
            return False
        await db.collection(self.user_collection).document(uid).set(user_data)
        return True
        
    async def update_user(self, uid: str, update_data: dict) -> bool | None:
        pass

    async def delete_user(self, uid: str) -> bool | None:
        pass

    async def get_user_by_username(self, username: str) -> dict | None:
        pass

user_repo = UserRepository()