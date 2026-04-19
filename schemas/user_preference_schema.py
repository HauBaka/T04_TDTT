from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

# Mức độ chịu đựng thời tiết xấu của người dùng
class WeatherTolerance(str, Enum):
    LOW = "thap"
    MEDIUM = "trung_binh"
    HIGH = "cao"

# Các sự kiện hành vi của người dùng có thể ghi nhận để cải thiện cá nhân hóa
class UserEventType(str, Enum):
    VIEW = "xem"
    CLICK = "nhan"
    SAVE = "luu"
    REMOVE = "xoa"
    BOOK = "dat_phong"
    RATE = "danh_gia"

# Schema lưu trữ sở thích bền vững của người dùng (lấy từ form)
class UserTravelPreference(BaseModel):
    weather_tolerance: WeatherTolerance = WeatherTolerance.MEDIUM
    preferred_amenities: list[str] = Field(default_factory=list)
    must_have_amenities: list[str] = Field(default_factory=list)
    excluded_amenities: list[str] = Field(default_factory=list)
    preferred_location_tags: list[str] = Field(default_factory=list)
    disliked_location_tags: list[str] = Field(default_factory=list)
    notes: str | None = None

# Schema lưu trữ hồ sơ du lịch của người dùng
class UserProfileSchema(BaseModel):
    uid: str
    travel_profile: UserTravelPreference | None = None
    survey_updated_at: datetime | None = None

# Schema lưu trữ các sự kiện hành vi của người dùng
class UserBehaviorEvent(BaseModel):
    event_type: UserEventType
    hotel_id: str | None = None
    hotel_name: str | None = None
    collection_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    value: float | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

# Trọng số các yếu tố khi tính điểm cá nhân hóa
class ScoringWeights(BaseModel):
    real_rating: float = 0.32
    profile_match: float = 0.16
    trip_match: float = 0.18
    collection_affinity: float = 0.14
    history_affinity: float = 0.10
    weather_fit: float = 0.10
