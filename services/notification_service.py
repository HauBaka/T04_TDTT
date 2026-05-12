from datetime import datetime, timezone
from core.exceptions import NotFoundError, AppException
from schemas.notification_schema import NotificationResponse, NotificationType, UpdateNotificationRequest
from schemas.response_schema import ResponseSchema
from repositories.notification_repo import notification_repo

class NotificationService:
    def __init__(self):
        self.notification_repository = notification_repo
    
    async def create_notification(self, user_id: str, notification_data: dict) -> ResponseSchema[NotificationResponse]:
        """Tạo một thông báo mới."""
        # Prepare data for database
        notification_db_data = {
            "receiver_id": user_id,
            "send_at": datetime.now(timezone.utc),
            "type": notification_data.get("type"),
            "content": notification_data.get("content"),
            "read": False,
            "ref_id": notification_data.get("ref_id"),
            "actor_id": notification_data.get("actor_id", "system")
        }
        
        # Create in database
        created_notification = await self.notification_repository.create(notification_db_data)
        return self.build_notification_response(created_notification, status_code=201, message="Notification created successfully")

    async def update_notification(self, notification_id: str, user_id: str, update_request: UpdateNotificationRequest) -> ResponseSchema[NotificationResponse]:
        """Cập nhật trạng thái của một thông báo cụ thể (ví dụ: đánh dấu đã đọc)."""
        # Get notification from database
        notification = await self.notification_repository.get_by_id(notification_id)
        if not notification:
            raise NotFoundError("Notification not found.")
        
        # Check permission - only the recipient can update
        if user_id != notification.get("receiver_id"):
            raise AppException(status_code=403, message="You do not have permission to update this notification.")
        
        if update_request.read is False:
            raise AppException(status_code=400, message="Cannot update notification to unread.")
        
        if notification.get("read") is True:
            raise AppException(status_code=400, message="Notification is already marked as read.")
        
        # Update in database
        update_data = {
            "read": update_request.read
        }
        updated_notification = await self.notification_repository.update(notification_id, update_data)
        
        return self.build_notification_response(updated_notification, status_code=200, message="Notification updated successfully")
    
    async def delete_notification(self, notification_id: str, user_id: str) -> ResponseSchema[bool]:
        """Xóa một thông báo cụ thể."""
        # Get notification from database
        notification = await self.notification_repository.get_by_id(notification_id)
        if not notification:
            raise NotFoundError("Notification not found.")
        
        # Check permission - only the recipient can delete
        if user_id != notification.get("receiver_id"):
            raise AppException(status_code=403, message="You do not have permission to delete this notification.")
        
        # Delete from database
        result = await self.notification_repository.delete(notification_id)
        
        return ResponseSchema[bool](
            status_code=200,
            message="Notification deleted successfully",
            data=result
        )

    def build_notification_object(self, notification_data: dict) -> NotificationResponse:
        """Xây dựng đối tượng thông báo từ dữ liệu thô."""
        notification = NotificationResponse(
            id=notification_data.get("id", ""),
            send_at=notification_data.get("send_at", datetime.now(timezone.utc)),
            type=NotificationType(notification_data.get("type")),
            content=notification_data.get("content"),
            read=notification_data.get("read", False),
            ref_id=notification_data.get("ref_id"),
            actor_id=notification_data.get("actor_id")
        )
        return notification

    def build_notification_response(self, notification_data: dict, status_code: int = 200, message: str = "Success") -> ResponseSchema[NotificationResponse]:
        """Xây dựng response từ notification data."""
        if not notification_data:
            raise NotFoundError("Notification not found.")
        
        return ResponseSchema[NotificationResponse](
            status_code=status_code,
            message=message,
            data=self.build_notification_object(notification_data)
        )

notification_service = NotificationService()