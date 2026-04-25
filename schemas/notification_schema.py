from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class NotificationType(str, Enum):
    SYSTEM = "system"
    INVITATION = "invitation"
    COLLECTION_UPDATE = "collection update"
    CONVERSATION_MESSAGE = "conversation message"
    TRIP_UPDATE = "trip update"

class NotificationResponse(BaseModel):
    id: str
    send_at: datetime
    type: NotificationType
    content: str
    read: bool = False
    ref_id: str
    actor_id: str

class UpdateNotificationRequest(BaseModel):
    read: bool