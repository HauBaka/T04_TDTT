from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from enum import Enum

from schemas.discover_schema import AIReviewSummary, AISentimentResult, AISentimentResult, BookingSource, GPSCoordinates, HotelImage, UserReview
from schemas.response_schema import UserPreviewResponse
from schemas.view_schema import ViewResponse

# --- DATATYPES
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
    model_config = ConfigDict(from_attributes=True)

    uid: str
    lat: float | None = None
    lng: float | None = None
    updated_at: datetime
    status: MemberTrackingStatus = MemberTrackingStatus.NO_SHARE

# --- DOCUMENTS
class TripMemberDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uid: str
    tracking: TripMemberTracking | None = None
    joined_at: datetime


class TripDocument(BaseModel):
    """trips/{trip_id}"""
    model_config = ConfigDict(from_attributes=True)

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

# --- RESPONSE
class TripPlaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    place_id: str = Field(validation_alias="property_token")

    name: str
    description: str | None = None
    link: str | None = None
    address: str | None = None
    phone: str | None = None
    gps_coordinates: GPSCoordinates | None = None
    # Nhận phòng & Trả phòng
    check_in_time: str | None = None
    check_out_time: str | None = None
    price: float # json_data -> rate_per_night.extracted_lowest
    deal: str | None = None
    booking_sources: list[BookingSource] = [] # Danh sách giá ở các trang khác
    # ảnh & Tiện ích
    images: list[HotelImage] = [] 
    amenities: list[str] = []
        # Reviews gốc
    raw_rating: float = 0.0 # trung bình từ các user reviews
    user_reviews: list[UserReview] = [] # Danh sách review gốc (chưa phân tích)

    # Ai phân tích lại
    ai_sentiment: AISentimentResult | None = None
    ai_summary: AIReviewSummary | None = None     # Tóm tắt do AI tạo ra, có thể hết hạn và cần được làm mới

    # views
    views: ViewResponse = Field(default_factory=ViewResponse)
class TripResponse(BaseModel):
    id: str
    owner_uid: str
    name: str
    place: Optional[TripPlaceResponse] = None

    start_at: datetime
    end_at: datetime

    status: TripStatus = TripStatus.WAITING
    member_count: int = 0

    created_at: datetime
    updated_at: datetime

class TripMemberResponse(UserPreviewResponse):
    tracking: TripMemberTracking | None = None
    joined_at: datetime

# --- REQUEST
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
    member_uids: list[str] = Field(..., min_length=1, description="Danh sách UID thành viên muốn xóa. Không được để rỗng.")
    
class TripUpdateRequest(BaseModel):
    """Chỉ owner mới được gọi và chỉ khi status là WAITING"""
    name: str | None = None
    place_id: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: TripStatus | None = None