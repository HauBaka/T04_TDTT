from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from enum import Enum

from schemas.response_schema import UserPreviewResponse

# --- DATATYPES
class ConversationRole(str, Enum):
    OWNER = "owner"
    MEMBER = "member"

class AttachmentType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
    PLACE = "place"  # Đính kèm địa điểm, có thể chứa place_id để liên kết đến thông tin địa điểm trong hệ thống

class ConversationMessageAttachment(BaseModel):
    type: AttachmentType
    value: str  # URL của tệp đính kèm hoặc ID của địa điểm nếu type là "place"

# --- REQUEST
class ConversationCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=32)
    description: str | None = Field(None, max_length=512)
    thumbnail_url: str | None = None

class ConversationUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=32)
    description: str | None = Field(None, max_length=512)
    thumbnail_url: str | None = None

class AddMembersRequest(BaseModel):
    member_uids: list[str] = Field(..., min_length=1, max_length=10, description="Danh sách UID của các thành viên cần thêm vào conversation. Tối đa 10 thành viên mỗi lần thêm.")

class RemoveMembersRequest(BaseModel):
    member_uids: list[str] = Field(..., min_length=1, max_length=10, description="Danh sách UID của các thành viên cần xóa khỏi conversation. Tối đa 10 thành viên mỗi lần xóa.")

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="Nội dung tin nhắn. Tối đa 2000 ký tự.")
    attachments: list[ConversationMessageAttachment] = Field(default_factory=list, min_length=0, max_length=5, description="Danh sách các tệp đính kèm cho tin nhắn. Tối đa 5 tệp đính kèm mỗi tin nhắn.")
    
# --- DOCUMENTS
class ConversationMemberDocument(BaseModel):
    uid: str
    role: ConversationRole = ConversationRole.MEMBER
    joined_at: datetime

class ConversationMessageDocument(BaseModel):
    """conversations/{conversation_id}/messages/{message_id}"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    sender_uid: str
    content: str
    sent_at: datetime
    attachments: list[ConversationMessageAttachment] = Field(default_factory=list, min_length=0, max_length=5)  # Danh sách các tệp đính kèm (nếu có)


class ConversationDocument(BaseModel):
    """conversations/{conversation_id}"""
    model_config = ConfigDict(from_attributes=True)

    id: str 
    owner_uid: str

    name: str
    description: str | None = None
    thumbnail_url: str | None = None

    created_at: datetime
    updated_at: datetime

    member_uids: list[str] = Field(default_factory=list)  # Chỉ lưu UID của thành viên trong document gốc để tối ưu truy vấn, thông tin chi tiết sẽ được lấy từ sub-collection "members"

class UserConversationSummaryDocument(BaseModel):
    """users/{uid}/conversations/{conversation_id}"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    thumbnail_url: str | None = None
    unread_count: int = 0
    latest_msg: ConversationMessageDocument | None = None
    last_updated: datetime = Field(default_factory=datetime.now)

# --- RESPONSE
class ConversationResponse(BaseModel):
    id: str
    owner_uid: str
    name: str
    description: str | None = None
    thumbnail_url: str | None = None
    created_at: datetime
    updated_at: datetime
    member_count: int = 0

class ConversationMemberResponse(UserPreviewResponse):
    role: ConversationRole
    joined_at: datetime

class ConversationMessageResponse(BaseModel):
    id: str
    sender: ConversationMemberResponse
    content: str
    sent_at: datetime
    attachments: list[ConversationMessageAttachment] = Field(default_factory=list, min_length=0, max_length=5)

# --- OTHER
class UserConversationSummaryUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str | None = None
    description: str | None = None
    thumbnail_url: str | None = None
    latest_msg: ConversationMessageDocument | None = None
    unread_count: int | None = None
    updated_at: datetime = Field(default_factory=datetime.now)