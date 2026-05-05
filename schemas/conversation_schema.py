from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class ConversationRole(str, Enum):
    OWNER = "owner"
    MEMBER = "member"

class ConversationMember(BaseModel):
    uid: str
    role: ConversationRole = ConversationRole.MEMBER
    joined_at: datetime
    # TODO: update các field dưới đây, mỗi khi GET conversation để đảm bảo thông tin của member luôn được cập nhật


class AttachmentType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
    PLACE = "place"  # Đính kèm địa điểm, có thể chứa place_id để liên kết đến thông tin địa điểm trong hệ thống

class ConversationMessageAttachment(BaseModel):
    type: AttachmentType
    value: str  # URL của tệp đính kèm hoặc ID của địa điểm nếu type là "place"

class ConversationMessage(BaseModel):
    sender_uid: str
    content: str
    sent_at: datetime
    attachments: list[ConversationMessageAttachment] = Field(default_factory=list, min_length=0, max_length=5)  # Danh sách các tệp đính kèm (nếu có)

class ConversationCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=32)
    description: str | None = Field(None, max_length=512)
    thumbnail_url: str | None = None

class ConversationUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=32)
    description: str | None = Field(None, max_length=512)
    thumbnail_url: str | None = None

class ConversationResponse(BaseModel):
    id: str
    owner_uid: str
    name: str
    description: str | None = None
    thumbnail_url: str | None = None
    created_at: datetime
    updated_at: datetime
    members: list[ConversationMember] = Field(default_factory=list)

class AddMembersRequest(BaseModel):
    member_uids: list[str] = Field(..., min_length=1, max_length=10, description="Danh sách UID của các thành viên cần thêm vào conversation. Tối đa 10 thành viên mỗi lần thêm.")

class RemoveMembersRequest(BaseModel):
    member_uids: list[str] = Field(..., min_length=1, max_length=10, description="Danh sách UID của các thành viên cần xóa khỏi conversation. Tối đa 10 thành viên mỗi lần xóa.")

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="Nội dung tin nhắn. Tối đa 2000 ký tự.")
    attachments: list[ConversationMessageAttachment] = Field(default_factory=list, min_length=0, max_length=5, description="Danh sách các tệp đính kèm cho tin nhắn. Tối đa 5 tệp đính kèm mỗi tin nhắn.")
    