from core.database import get_db

class CollectionRepository:
    def __init__(self):
        pass

    def _get_db(self):
        return get_db()

    async def create_collection(self, uid: str, collection_request: dict) -> dict:
        """Tạo một collection mới cho người dùng."""
        return {}

    async def update_collection(self, uid: str, collection_id: str, update_data: dict) -> dict:
        """Cập nhật một collection của người dùng."""
        return {}

    async def delete_collection(self, uid: str, collection_id: str):
        """Xóa một collection của người dùng."""
        pass
    
    async def get_collection(self, collection_id: str) -> dict:
        """Lấy thông tin của một collection cụ thể."""
        return {}

collection_repo = CollectionRepository()