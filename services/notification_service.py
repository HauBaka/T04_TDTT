from core.exceptions import AppException, BadRequestError, PermissionDeniedError
from repositories.notification_repo import notification_repo
from schemas.notification_schema import (
    NotificationCreateRequest,
    NotificationDocument,
    NotificationResponse,
    NotificationUpdateRequest,
)
from schemas.response_schema import ResponseSchema


class NotificationService:
    def __init__(self):
        self.notification_repository = notification_repo

    async def create_notification(
        self, notification_request: NotificationCreateRequest
    ) -> ResponseSchema[NotificationResponse]:
        """Tạo một thông báo mới."""
        notification = await self.notification_repository.create(notification_request)
        return self.build_notification_response(notification)

    async def update_notification(
        self,
        notification_id: str,
        user_id: str,
        update_request: NotificationUpdateRequest,
    ) -> ResponseSchema[NotificationResponse]:
        """Cập nhật trạng thái của một thông báo cụ thể (ví dụ: đánh dấu đã đọc)."""
        # Get notification from database
        notification = await self.notification_repository.get_by_id(
            user_id, notification_id
        )

        # Check permission - only the recipient can update
        if user_id != notification.receiver_id:
            raise PermissionDeniedError(
                "You do not have permission to update this notification."
            )

        if not update_request.read:
            raise AppException(
                status_code=400, message="Cannot update notification to unread."
            )

        if notification.read:
            raise AppException(
                status_code=400, message="Notification is already marked as read."
            )

        updated_notification = await self.notification_repository.update(
            user_id, notification_id, update_request
        )

        return self.build_notification_response(updated_notification)

    async def create_batch_notifications(
        self, request: list[NotificationCreateRequest]
    ) -> list[NotificationResponse]:
        """Tạo nhiều thông báo cùng lúc."""
        if not request:
            raise BadRequestError("Request list cannot be empty.")

        notifications = await self.notification_repository.create_batch(
            requests=request
        )

        # Convert to response objects for callers that expect NotificationResponse
        return [self.build_notification_object(n) for n in notifications]

    async def delete_notification(
        self, notification_id: str, user_id: str
    ) -> ResponseSchema[bool]:
        """Xóa một thông báo cụ thể."""
        # Get notification from database
        notification = await self.notification_repository.get_by_id(
            user_id, notification_id
        )

        # Check permission - only the recipient can delete
        if user_id != notification.receiver_id:
            raise PermissionDeniedError(
                "You do not have permission to delete this notification."
            )

        # Delete from database
        await self.notification_repository.delete(user_id, notification_id)

        return ResponseSchema[bool](data=True)

    def build_notification_object(
        self, notification_data: NotificationDocument
    ) -> NotificationResponse:
        """Xây dựng đối tượng thông báo từ dữ liệu thô."""
        return NotificationResponse(
            id=notification_data.id,
            receiver_id=notification_data.receiver_id,
            send_at=notification_data.send_at,
            type=notification_data.type,
            content=notification_data.content,
            read=notification_data.read,
            ref_id=notification_data.ref_id,
            actor_id=notification_data.actor_id,
        )

    def build_notification_response(
        self, notification_data: NotificationDocument
    ) -> ResponseSchema[NotificationResponse]:
        """Xây dựng response từ notification data."""

        return ResponseSchema(data=self.build_notification_object(notification_data))


notification_service = NotificationService()
