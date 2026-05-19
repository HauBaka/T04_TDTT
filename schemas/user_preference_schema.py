from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field

# Mức độ chịu đựng thời tiết xấu của người dùng
class WeatherTolerance(str, Enum):
    LOW = "thap"
    MEDIUM = "trung_binh"
    HIGH = "cao"

# Schema lưu trữ sở thích bền vững của người dùng (lấy từ form)
class UserTravelPreference(BaseModel):
    weather_tolerance: WeatherTolerance = WeatherTolerance.MEDIUM
    preferred_amenities: list[str] = Field(default_factory=list)
    must_have_amenities: list[str] = Field(default_factory=list)
    excluded_amenities: list[str] = Field(default_factory=list)
    preferred_location_tags: list[str] = Field(default_factory=list)
    disliked_location_tags: list[str] = Field(default_factory=list)
    notes: str | None = None

# Trọng số các yếu tố khi tính điểm cá nhân hóa
class ScoringWeights(BaseModel):
    real_rating: float = 0.32
    profile_match: float = 0.16
    trip_match: float = 0.18
    collection_affinity: float = 0.14
    history_affinity: float = 0.10
    weather_fit: float = 0.10
