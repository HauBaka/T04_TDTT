
from fastapi import APIRouter, Depends
from schemas.response_schema import ResponseSchema
from core.dependencies import get_current_user
from services.notification_service import notification_service
from schemas.notification_schema import NotificationResponse, UpdateNotificationRequest

notification_router = APIRouter()

@notification_router.patch("/users/me/notifications/{notification_id}", response_model=ResponseSchema[NotificationResponse])
async def update_notification(notification_id: str, update_request: UpdateNotificationRequest, requester=Depends(get_current_user(optional=False))):
    """Cập nhật trạng thái của một thông báo cụ thể (ví dụ: đánh dấu đã đọc)."""
    return await notification_service.update_notification(notification_id, requester.get("uid"), update_request)

