from pydantic import BaseModel, ConfigDict
from datetime import datetime
from enum import Enum

class NotificationType(str, Enum):
    SYSTEM = "system"
    INVITATION = "invitation"
    COLLECTION_UPDATE = "collection update"
    CONVERSATION_MESSAGE = "conversation message"
    TRIP_UPDATE = "trip update"

class NotificationDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    receiver_id: str
    send_at: datetime
    type: NotificationType
    content: str
    read: bool = False
    ref_id: str
    actor_id: str

class NotificationResponse(BaseModel):
    id: str
    receiver_id: str
    send_at: datetime
    type: NotificationType
    content: str
    read: bool = False
    ref_id: str
    actor_id: str

class NotificationCreateRequest(BaseModel):
    receiver_id: str
    type: NotificationType
    content: str
    ref_id: str
    actor_id: str

class NotificationUpdateRequest(BaseModel):
    read: bool