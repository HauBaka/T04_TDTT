from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from schemas.discover_schema import (
    AIReviewSummary,
    AISentimentResult,
    BookingSource,
    GPSCoordinates,
    HotelImage,
    UserReview,
)
from schemas.response_schema import UserPreviewResponse
from schemas.view_schema import ViewResponse


# --- DATATYPES
class ModifyAction(str, Enum):
    """Định nghĩa các hành động có thể thực hiện khi cập nhật collection."""

    ADD = "add"
    REMOVE = "remove"


class TargetType(str, Enum):
    PLACE = "place"
    COLLABORATOR = "collaborator"
    TAG = "tag"


class Modification(BaseModel):
    """Định nghĩa cấu trúc dữ liệu cho việc cập nhật collection."""

    target_id: str
    target_type: TargetType  # "place", "collaborator", hoặc "tag"
    action: ModifyAction


class CollectionVisibility(str, Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


# --- DOCUMENT
class CollectionSaverDocument(BaseModel):
    """Thông tin về người dùng đã lưu collection.
    collections/{collection_id}/savers/{uid}
    """

    uid: str
    saved_at: datetime


class CollectionContributorDocument(BaseModel):
    """Thông tin về người dùng đã đóng góp vào collection.
    collections/{collection_id}/contributors/{uid}
    """

    uid: str
    contributed_count: int = (
        0  # số lượng địa điểm mà cộng tác viên đã thêm vào collection
    )
    joined_at: datetime  # thời điểm cộng tác viên được thêm vào collection


class CollectionPlaceDocument(BaseModel):
    """Thông tin về địa điểm đã được thêm vào collection."""

    place_id: str
    added_at: datetime
    added_by: str  # uid của người dùng đã thêm địa điểm này vào collection


class CollectionDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_uid: str

    name: str = Field(..., min_length=3, max_length=32)
    description: str | None = Field(None, max_length=512)
    thumbnail_url: str | None = None

    created_at: datetime
    updated_at: datetime

    saved_count: int = 0
    saver_uids: list[str] = Field(default_factory=list)
    contributor_count: int = 0
    contributor_uids: list[str] = Field(default_factory=list)
    place_count: int = 0
    place_ids: list[str] = Field(default_factory=list)

    tags: list[str] = Field(default_factory=list)
    visibility: CollectionVisibility = CollectionVisibility.PUBLIC
    views: ViewResponse = Field(default_factory=ViewResponse)


# --- RESPONSE
class CollectionContributorResponse(UserPreviewResponse):
    contributed_count: int = 0
    joined_at: datetime


class CollectionSaverResponse(UserPreviewResponse):
    saved_at: datetime


class CollectionPlaceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    place_id: str = Field(validation_alias="property_token")
    added_at: datetime
    added_by: UserPreviewResponse | None = None

    name: str
    description: str | None = None
    link: str | None = None
    address: str | None = None
    phone: str | None = None
    gps_coordinates: GPSCoordinates | None = None
    # Nhận phòng & Trả phòng
    check_in_time: str | None = None
    check_out_time: str | None = None
    price: float  # json_data -> rate_per_night.extracted_lowest
    deal: str | None = None
    booking_sources: list[BookingSource] = []  # Danh sách giá ở các trang khác
    # ảnh & Tiện ích
    images: list[HotelImage] = []
    amenities: list[str] = []
    # Reviews gốc
    raw_rating: float = 0.0  # trung bình từ các user reviews
    user_reviews: list[UserReview] = []  # Danh sách review gốc (chưa phân tích)

    # Ai phân tích lại
    ai_sentiment: AISentimentResult | None = None
    ai_summary: AIReviewSummary | None = (
        None  # Tóm tắt do AI tạo ra, có thể hết hạn và cần được làm mới
    )

    # views
    views: ViewResponse = Field(default_factory=ViewResponse)


class CollectionPublicResponse(BaseModel):
    id: str
    owner_uid: str

    name: str = Field(..., min_length=3, max_length=32)
    description: str | None = Field(None, max_length=512)
    thumbnail_url: str | None = None

    created_at: datetime
    updated_at: datetime

    saved_count: int = 0
    contributor_count: int = 0
    place_count: int = 0
    views: ViewResponse = Field(default_factory=ViewResponse)

    tags: list[str] = Field(default_factory=list)
    visibility: CollectionVisibility = CollectionVisibility.PUBLIC


class CollectionUnlistedResponse(CollectionPublicResponse):
    pass


class CollectionPrivateResponse(CollectionPublicResponse):
    pass


# --- REQUEST
class CollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=32)
    description: str | None = Field(None, max_length=512)
    tags: list[str] = Field(default_factory=list)
    visibility: CollectionVisibility = CollectionVisibility.PUBLIC
    thumbnail_url: str | None = None


class CollectionUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=32)
    description: str | None = Field(None, max_length=512)
    visibility: CollectionVisibility | None = None
    thumbnail_url: str | None = None


class AddMultiplePlacesRequest(BaseModel):
    place_ids: list[str] = Field(..., min_length=1, max_length=50)


class AddMultipleContributorsRequest(BaseModel):
    contributor_uids: list[str] = Field(..., min_length=1, max_length=50)


class AddMultipleTagsRequest(BaseModel):
    tags: list[str] = Field(..., min_length=1, max_length=50)


class RemoveMultiplePlacesRequest(BaseModel):
    place_ids: list[str] = Field(..., min_length=1, max_length=50)


class RemoveMultipleContributorsRequest(BaseModel):
    contributor_uids: list[str] = Field(..., min_length=1, max_length=50)


class RemoveMultipleTagsRequest(BaseModel):
    tags: list[str] = Field(..., min_length=1, max_length=50)


class CollectionResponse(BaseModel):
    collection: (
        CollectionPublicResponse
        | CollectionUnlistedResponse
        | CollectionPrivateResponse
    )
