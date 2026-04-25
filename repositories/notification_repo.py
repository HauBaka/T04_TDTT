from repositories.base_repo import BaseRepository

class NotificationRepository(BaseRepository):
    def __init__(self):
        super().__init__("notifications")

    async def create(self, notification_data: dict) -> dict:
        """Tạo một thông báo mới."""
        return {}
    
    async def get_by_id(self, notification_id: str) -> dict:
        """Lấy thông tin một thông báo theo ID."""
        return {}
    
    async def update(self, notification_id: str, update_data: dict) -> dict:
        """Cập nhật thông tin một thông báo."""
        return {}

    async def delete(self, notification_id: str) -> bool:
        """Xóa một thông báo."""
        return True
    
notification_repo = NotificationRepository()