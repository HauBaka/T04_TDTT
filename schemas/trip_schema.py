from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class TripStatus(str, Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    ENDED = "ended"

class MemberTrackingStatus(str, Enum):
    ACTIVE = "active"             # Đang di chuyển/online
    LOST_SIGNAL = "lost_signal"   # Mất tín hiệu (dựa trên updated_at)
    WRONG_DIRECTION = "wrong_direction" # Đi sai hướng
    ARRIVED = "arrived"           # Đã đến đích (place_id)
    LEFT = "left"                 # Đã rời hoạt động
    NO_SHARE = "no_share"         # Không chia sẻ vị trí

class TripMemberTracking(BaseModel):
    """
    Dữ liệu vị trí realtime của từng thành viên.
    Lưu tại: trips/{trip_id}/members/{uid}
    """
    uid: str
    lat: float
    lng: float
    updated_at: datetime
    status: MemberTrackingStatus = MemberTrackingStatus.NO_SHARE
    
    # Thông tin bổ sung để hiển thị trên bản đồ mà không cần fetch UserRepo
    display_name: str | None = None
    avatar_url: str | None = None

class TripCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    place_id: str = Field(..., description="ID địa điểm đích đến")
    start_at: datetime
    end_at: datetime
class TripAddMembersRequest(BaseModel):
    """schema dùng cho API thêm thành viên"""
    member_uids: list[str] = Field(...,min_length=1,description="Danh sách UID thành viên muốn thêm. Không được để rỗng.")
    
class TripRemoveMembersRequest(BaseModel):
    """Schema dùng cho API xóa thành viên"""
    target_uids: list[str] = Field(..., min_length=1, description="Danh sách UID thành viên muốn xóa. Không được để rỗng.")
    
class TripUpdateRequest(BaseModel):
    """Chỉ owner mới được gọi và chỉ khi status là WAITING"""
    name: str | None = None
    place_id: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: TripStatus | None = None

class TripResponse(BaseModel):
    id: str
    owner_uid: str
    name: str
    place_id: str
    start_at: datetime
    end_at: datetime
    status: TripStatus = TripStatus.WAITING
    
    member_uids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime