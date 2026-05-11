from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Mức độ chịu đựng thời tiết xấu của người dùng
class WeatherTolerance(str, Enum):
    LOW = "thap"
    MEDIUM = "trung_binh"
    HIGH = "cao"

# Các sự kiện hành vi của người dùng có thể ghi nhận để cải thiện cá nhân hóa
class UserEventType(str, Enum):
    VIEW = "xem"
    SAVE_PLACE = "luu_place"
    REMOVE_PLACE = "xoa_place"
    SAVE_COLLECTION = "luu_collection"
    REMOVE_COLLECTION = "xoa_collection"

# Schema lưu trữ sở thích bền vững của người dùng (lấy từ form)
class UserTravelPreference(BaseModel):
    weather_tolerance: WeatherTolerance = WeatherTolerance.MEDIUM
    preferred_amenities: list[str] = Field(default_factory=list)
    must_have_amenities: list[str] = Field(default_factory=list)
    excluded_amenities: list[str] = Field(default_factory=list)
    preferred_location_tags: list[str] = Field(default_factory=list)
    disliked_location_tags: list[str] = Field(default_factory=list)
    notes: str | None = None

# Schema lưu trữ các sự kiện hành vi của người dùng
class UserBehaviorEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    event_type: UserEventType
    target_id: str | None = None
    target_name: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str] = Field(default_factory=dict)

# Trọng số các yếu tố khi tính điểm cá nhân hóa
class ScoringWeights(BaseModel):
    real_rating: float = 0.32
    profile_match: float = 0.16
    trip_match: float = 0.18
    collection_affinity: float = 0.14
    history_affinity: float = 0.10
    weather_fit: float = 0.10
