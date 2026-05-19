from google.cloud import firestore
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

    async def create(self, notification_request: NotificationCreateRequest) -> NotificationDocument:
        """Tạo một thông báo mới."""
        notification_doc = NotificationDocument(
            id=self._collection.document().id,
            receiver_id=notification_request.receiver_id,
            send_at=self._current_timestamp,
            type=notification_request.type,
            content=notification_request.content,
            read=False,
            ref_id=notification_request.ref_id,
            actor_id=notification_request.actor_id
        )
        await self._create(notification_doc.model_dump(mode = "python", exclude_none=False), doc_id=notification_doc.id)
        return notification_doc
    
    async def create_batch(self, requests: list[NotificationCreateRequest]) -> list[NotificationDocument]:
        """Tạo nhiều thông báo cùng lúc."""
        if not requests:
            return []

        batch = self._db.batch()
        now = self._current_timestamp
        notifications = []

        for req in requests:
            doc_ref = self._collection.document()
            notification_doc = NotificationDocument(
                id=doc_ref.id,
                receiver_id=req.receiver_id,
                send_at=now,
                type=req.type,
                content=req.content,
                read=False,
                ref_id=req.ref_id,
                actor_id=req.actor_id
            )
            batch.create(doc_ref, notification_doc.model_dump(mode="python", exclude_none=False))
            notifications.append(notification_doc)

        await self._commit_batch(batch)
        return notifications

    async def get_by_id(self, notification_id: str) -> NotificationDocument:
        """Lấy thông tin một thông báo theo ID."""
        data = await self._get_by_id(notification_id)
        try:
            return NotificationDocument.model_validate(data)
        except PydanticValidationError as e:
            logger.error(f"Error validating notification data for {notification_id}: {str(e)}")
            raise ValidationError("Invalid notification data")
    
    async def update(self, notification_id: str, update_request: NotificationUpdateRequest) -> NotificationDocument:
        """Cập nhật thông tin một thông báo."""
        update_data = update_request.model_dump(mode="python", exclude_none=True)
        if not update_data:
            raise ValueError("No valid fields to update.")
        
        update_data["updated_at"] = self._current_timestamp
        await self._update(notification_id, update_data)
        return await self.get_by_id(notification_id)

    async def delete(self, notification_id: str) -> bool:
        """Xóa một thông báo."""
        notification_ref = self._collection.document(notification_id)
        await notification_ref.delete()
        return True
    
notification_repo = NotificationRepository()