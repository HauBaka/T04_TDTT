from core.database import get_db

class UserRepository:
    def __init__(self):
        self.user_collection = "users"

    def _get_db(self):
        return get_db()
    
    async def get_user(self, uid: str) -> dict | None:
        doc = self._get_db().collection(self.user_collection).document(uid).get()
        return doc.to_dict() if doc.exists else None
    
    async def create_user(self, user_data: dict) -> str | None:
        uid = user_data.get("uid")
        if not uid:
            return None
        self._get_db().collection(self.user_collection).document(uid).set(user_data)
        return uid
        
    async def update_user(self, uid: str, update_data: dict) -> bool | None:
        try:
            self._get_db().collection(self.user_collection).document(uid).update(update_data)
            return True
        except Exception:
            return False

    async def delete_user(self, uid: str) -> bool | None:
        try:
            pending_data = {"status": "pending_delete", "is_deleted": True}
            self._get_db().collection(self.user_collection).document(uid).update(pending_data)
            return True
        except Exception:
            return False

    async def get_user_by_username(self, username: str) -> dict | None:
        docs = self._get_db().collection(self.user_collection).where("username", "==", username).limit(1).get()
        for doc in docs:
            return doc.to_dict()
        return None

user_repo = UserRepository()