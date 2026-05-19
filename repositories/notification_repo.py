from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import ValidationError
from repositories.base_repo import BaseRepository
from schemas.notification_schema import (
    NotificationCreateRequest,
    NotificationDocument,
    NotificationUpdateRequest,
)


class NotificationRepository(BaseRepository):
    def __init__(self):
        super().__init__("notifications")

    def _get_user_notifications_collection(self, user_id: str):
        """Hàm helper để lấy tham chiếu đến subcollection notifications của một user cụ thể."""
        return (
            self._db.collection("users").document(user_id).collection("notifications")
        )

    async def create(
        self, notification_request: NotificationCreateRequest
    ) -> NotificationDocument:
        """Tạo một thông báo mới vào subcollection của user."""
        user_collection = self._get_user_notifications_collection(
            notification_request.receiver_id
        )
        doc_ref = user_collection.document()

        notification_doc = NotificationDocument(
            id=doc_ref.id,
            receiver_id=notification_request.receiver_id,
            send_at=self._current_timestamp,
            type=notification_request.type,
            content=notification_request.content,
            read=False,
            ref_id=notification_request.ref_id,
            actor_id=notification_request.actor_id,
        )

        await doc_ref.set(
            notification_doc.model_dump(mode="python", exclude_none=False)
        )
        return notification_doc

    async def create_batch(
        self, requests: list[NotificationCreateRequest]
    ) -> list[NotificationDocument]:
        """Tạo nhiều thông báo cùng lúc vào đúng subcollection của từng User tương ứng."""
        if not requests:
            return []

        batch = self._db.batch()
        now = self._current_timestamp
        notifications = []

        for req in requests:
            doc_ref = self._get_user_notifications_collection(
                req.receiver_id
            ).document()

            notification_doc = NotificationDocument(
                id=doc_ref.id,
                receiver_id=req.receiver_id,
                send_at=now,
                type=req.type,
                content=req.content,
                read=False,
                ref_id=req.ref_id,
                actor_id=req.actor_id,
            )
            batch.create(
                doc_ref, notification_doc.model_dump(mode="python", exclude_none=False)
            )
            notifications.append(notification_doc)

        await self._commit_batch(batch)
        return notifications

    async def get_by_id(
        self, user_id: str, notification_id: str
    ) -> NotificationDocument:
        """Lấy thông tin một thông báo từ subcollection theo User ID và Notification ID."""
        doc_ref = self._get_user_notifications_collection(user_id).document(
            notification_id
        )
        doc_snapshot = await doc_ref.get()
        if not doc_snapshot.exists:
            from core.exceptions import NotFoundError

            raise NotFoundError(
                message=f"Notification {notification_id} not found for user {user_id}"
            )

        data = doc_snapshot.to_dict() or {}
        data["id"] = doc_snapshot.id
        try:
            return NotificationDocument.model_validate(data)
        except PydanticValidationError as e:
            logger.error(
                f"Error validating notification data for user {user_id}, doc {notification_id}: {str(e)}"
            )
            raise ValidationError("Invalid notification data")

    async def update(
        self,
        user_id: str,
        notification_id: str,
        update_request: NotificationUpdateRequest,
    ) -> NotificationDocument:
        """Cập nhật thông tin một thông báo bên trong subcollection."""
        update_data = update_request.model_dump(mode="python", exclude_none=True)
        if not update_data:
            raise ValueError("No valid fields to update.")

        update_data["updated_at"] = self._current_timestamp

        doc_ref = self._get_user_notifications_collection(user_id).document(
            notification_id
        )
        await doc_ref.update(update_data)

        return await self.get_by_id(user_id, notification_id)

    async def delete(self, user_id: str, notification_id: str) -> bool:
        """Xóa một thông báo khỏi subcollection của user."""
        doc_ref = self._get_user_notifications_collection(user_id).document(
            notification_id
        )
        await doc_ref.delete()
        return True


notification_repo = NotificationRepository()
