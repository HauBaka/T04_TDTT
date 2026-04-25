
from datetime import datetime

from schemas.notification_schema import NotificationResponse, NotificationType, UpdateNotificationRequest
from schemas.response_schema import ResponseSchema
from repositories.notification_repo import notification_repo

class NotificationService:
    def __init__(self):
        self.notification_repository = notification_repo

    async def get_notifications_for_user(self, user_id: str) -> ResponseSchema[list[NotificationResponse]]:
        """Lấy danh sách thông báo cho một người dùng."""
        return ResponseSchema(data=[
            NotificationResponse(
                id="notification_id_1",
                send_at=datetime.now(),
                type=NotificationType.INVITATION,
                content="Bạn có một lời mời mới",
                read=False,
                ref_id="ref_id_1",
                actor_id="actor_id_1"
            ),
            NotificationResponse(
                id="notification_id_2",
                send_at=datetime.now(),
                type=NotificationType.COLLECTION_UPDATE,
                content="Bộ sưu tập 'Địa điểm yêu thích' đã được cập nhật",
                read=True,
                ref_id="ref_id_2",
                actor_id="system"
            )
        ])
    
    async def create_notification(self, notification_data: dict) -> ResponseSchema[NotificationResponse]:
        """Tạo một thông báo mới."""
        return ResponseSchema(data=NotificationResponse(
            id="new_notification_id",
            send_at=datetime.now(),
            type=NotificationType.INVITATION,
            content=notification_data.get("content", "Bạn có một thông báo mới"),
            read=False,
            ref_id=notification_data.get("ref_id", "ref_id"),
            actor_id=notification_data.get("actor_id", "actor_id")
        ))

    async def update_notification(self, notification_id: str, user_id: str, update_request: UpdateNotificationRequest) -> ResponseSchema[NotificationResponse]:
        """Cập nhật trạng thái của một thông báo cụ thể (ví dụ: đánh dấu đã đọc)."""
        return ResponseSchema(data=NotificationResponse(
            id=notification_id,
            send_at=datetime.now(),
            type=NotificationType.INVITATION,
            content="Bạn có một lời mời mới",
            read=update_request.read,
            ref_id="ref_id",
            actor_id="actor_id"
        ))
    
    async def delete_notification(self, notification_id: str, user_id: str) -> ResponseSchema[bool]:
        """Xóa một thông báo cụ thể."""
        return ResponseSchema(data=True)

notification_service = NotificationService()