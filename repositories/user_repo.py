from core.database import get_db
from repositories.base_repo import BaseRepository
class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__("users")
    
    async def get_user(self, uid: str) -> dict | None:
        return await self._get_by_id(uid)
    
    async def create_user(self, user_data: dict) -> str | None:
        uid = user_data.get("uid")
        if not uid:
            return None
        await self._create(user_data, uid)
        return uid
        
    async def update_user(self, uid: str, update_data: dict) -> None:
        # NOTE: Để service xử lý exceptions
        await self._update(uid, update_data)

    async def delete_user(self, uid: str) -> bool:
        return await self._delete(uid)

    async def get_user_by_username(self, username: str) -> dict | None:
        docs = await self._collection.where("username_lower", "==", username.lower()).limit(1).get()
        for doc in docs:
            return doc.to_dict()
        return None

    async def get_user_by_email(self, email: str) -> dict | None:
        docs = await self._collection.where("email", "==", email.lower()).limit(1).get()

        for doc in docs:
            return doc.to_dict()
        return None

    async def get_users(self, uids: list[str]) -> dict[str, dict]:
        """Lấy thông tin nhiều người dùng từ danh sách uid."""
        if not uids:
            return {}
        
        users = {}
        for uid in uids:
            try:
                user = await self.get_user(uid)
                if user:
                    users[uid] = user
            except Exception as e:
                from loguru import logger
                logger.error(f"Error fetching user {uid}: {str(e)}")
        
        return users

user_repo = UserRepository()
