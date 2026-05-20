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


class UserTravelPreferenceUpdateRequest(BaseModel):
    """Schema dùng cho request tạo / cập nhật preference (tất cả trường optional để dễ partial update)."""

    weather_tolerance: WeatherTolerance | None = None
    preferred_amenities: list[str] | None = None
    must_have_amenities: list[str] | None = None
    excluded_amenities: list[str] | None = None
    preferred_location_tags: list[str] | None = None
    disliked_location_tags: list[str] | None = None
    notes: str | None = None


# class UserTravelPreferenceUpdateRequest(UserTravelPreferenceRequest):
#     """Schema đồng bộ cho endpoint update preference.

#     Tách riêng để API không nhận trực tiếp model lưu trữ.
#     """
#     pass


class TravelPreferenceOption(BaseModel):
    label: str


class TravelPreferenceQuestion(BaseModel):
    field: str
    question: str
    options: list[TravelPreferenceOption] = Field(default_factory=list)
    required: bool = False


class TravelPreferenceQuiz(BaseModel):
    questions: list[TravelPreferenceQuestion] = Field(default_factory=list)


class UserTravelPreferenceResponse(BaseModel):
    preference: UserTravelPreference


def build_default_travel_preference_quiz() -> TravelPreferenceQuiz:
    weather_options = [
        TravelPreferenceOption(label="Thấp"),
        TravelPreferenceOption(label="Trung bình"),
        TravelPreferenceOption(label="Cao"),
    ]

    amenity_options = [
        TravelPreferenceOption(label="WiFi"),
        TravelPreferenceOption(label="Bữa sáng"),
        TravelPreferenceOption(label="Hồ bơi"),
        TravelPreferenceOption(label="Spa"),
        TravelPreferenceOption(label="Phòng gym"),
        TravelPreferenceOption(label="Bãi đậu xe"),
        TravelPreferenceOption(label="Cho phép thú cưng"),
    ]

    location_options = [
        TravelPreferenceOption(label="Gần trung tâm thành phố"),
        TravelPreferenceOption(label="Gần bãi biển"),
        TravelPreferenceOption(label="Gần núi"),
        TravelPreferenceOption(label="Khu yên tĩnh"),
        TravelPreferenceOption(label="Gần phương tiện công cộng"),
    ]

    return TravelPreferenceQuiz(
        questions=[
            TravelPreferenceQuestion(
                field="weather_tolerance",
                question="Bạn chịu đựng thời tiết xấu như thế nào?",
                options=weather_options,
                required=True,
            ),
            TravelPreferenceQuestion(
                field="preferred_amenities",
                question="Bạn ưu tiên tiện nghi nào? (Chọn nhiều)",
                options=amenity_options,
            ),
            TravelPreferenceQuestion(
                field="must_have_amenities",
                question="Bạn bắt buộc phải có tiện nghi nào? (Nếu có)",
                options=amenity_options,
            ),
            TravelPreferenceQuestion(
                field="excluded_amenities",
                question="Bạn muốn tránh tiện nghi nào? (Nếu có)",
                options=amenity_options,
            ),
            TravelPreferenceQuestion(
                field="preferred_location_tags",
                question="Bạn thích khu vực nào? (Chọn nhiều)",
                options=location_options,
            ),
            TravelPreferenceQuestion(
                field="disliked_location_tags",
                question="Khu vực bạn không thích? (Nếu có)",
                options=location_options,
            ),
        ]
    )
