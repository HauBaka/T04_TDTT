from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class InvitationType(str, Enum):
    CONVERSATION = "conversation"
    COLLECTION = "collection"
    TRIP = "trip"

    @property
    def display_name(self) -> str:
        labels = {
            self.CONVERSATION: "Nhóm chat",
            self.COLLECTION: "Bộ sưu tập",
            self.TRIP: "Chuyến đi",
        }
        return labels.get(self, self.value)

    @property
    def invitation_label(self) -> str:
        return "đã mời bạn tham gia " + self.display_name.lower()


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"

    @property
    def display_name(self) -> str:
        labels = {
            self.PENDING: "Đang chờ",
            self.ACCEPTED: "Đã chấp nhận",
            self.DECLINED: "Đã từ chối",
            self.EXPIRED: "Đã hết hạn",
        }
        return labels.get(self, self.value)


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
    sender_uid: str = Field(..., description="UID của người gửi lời mời")
    target_uid: str = Field(..., description="UID của người nhận lời mời")
    type: InvitationType
    ref_id: str = Field(..., description="ID của Conversation, Collection hoặc Trip")
    expired_at: datetime = Field(..., description="Thời điểm hết hạn của lời mời")


class InvitationUpdateRequest(BaseModel):
    status: InvitationStatus


class GetPendingInvitationsRequest(BaseModel):
    target_uid: str = Field(..., description="UID của người nhận lời mời")
    actor_uid: str = Field(
        ..., description="UID của người thực hiện hành động (chấp nhận/từ chối)"
    )
    type: InvitationType = Field(
        ..., description="Loại lời mời (conversation, collection, trip)"
    )
    ref_id: str = Field(..., description="ID của Conversation, Collection hoặc Trip")


class InvitationResponse(BaseModel):
    id: str
    sender_uid: str
    target_uid: str
    type: InvitationType
    ref_id: str
    status: InvitationStatus = InvitationStatus.PENDING
    created_at: datetime
    expired_at: datetime
