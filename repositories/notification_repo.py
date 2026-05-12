from repositories.base_repo import BaseRepository

class NotificationRepository(BaseRepository):
    def __init__(self):
        super().__init__("notifications")

    async def create(self, notification_data: dict) -> dict:
        """Tạo một thông báo mới."""
        notification_id = await self._create(notification_data)
        notification_data["id"] = notification_id
        return notification_data
    
    async def get_by_id(self, notification_id: str) -> dict:
        """Lấy thông tin một thông báo theo ID."""
        return await self._get_by_id(notification_id)
    
    async def update(self, notification_id: str, update_data: dict) -> dict:
        """Cập nhật thông tin một thông báo."""
        await self._update(notification_id, update_data)
        return await self._get_by_id(notification_id)

    async def delete(self, notification_id: str) -> bool:
        """Xóa một thông báo."""
        return await self._delete(notification_id)
    
notification_repo = NotificationRepository()