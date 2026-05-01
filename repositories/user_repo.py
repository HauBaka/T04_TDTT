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
    async def get_users(self, uids: list[str]) -> dict[str, dict]:
        """
        Lấy thông tin của nhiều user cùng lúc.
        Trả về dict dạng map: { "uid_1": {user_data}, "uid_2": {user_data} }
        """
        if not uids:
            return {}
        unique_uids = list(set(uids))
        result = {}
        chunk_size = 30
        for i in range(0, len(unique_uids), chunk_size):
            chunk = unique_uids[i:i + chunk_size]
            docs = await self._collection.where("uid", "in", chunk).get()
            
            for doc in docs:
                user_data = doc.to_dict()
                # Thêm if để pass qua khâu check lỗi của Pylance
                if user_data: 
                    user_data["uid"] = doc.id 
                    result[doc.id] = user_data

        return result   
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

user_repo = UserRepository()
