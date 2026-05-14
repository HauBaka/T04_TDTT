from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class InvitationType(str, Enum):
    CONVERSATION = "conversation"
    COLLECTION = "collection"
    TRIP = "trip"

class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"

class InvitationDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sender_uid: str
    target_uid: str
    type: InvitationType
    ref_id: str
    status: InvitationStatus
    created_at: datetime
    updated_at: datetime
    expired_at: datetime

class InvitationCreateRequest(BaseModel):
    target_uid: str = Field(..., description="UID của người nhận lời mời")
    type: InvitationType
    ref_id: str = Field(..., description="ID của Conversation, Collection hoặc Trip")
    expired_at: datetime = Field(..., description="Thời điểm hết hạn của lời mời")

class InvitationUpdateRequest(BaseModel):
    status: InvitationStatus

class InvitationResponse(BaseModel):
    id: str
    sender_uid: str
    target_uid: str
    type: InvitationType
    ref_id: str
    status: InvitationStatus = InvitationStatus.PENDING
    created_at: datetime
    expired_at: datetime