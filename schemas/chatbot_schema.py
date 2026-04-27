from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field
from schemas.discover_schema import GPSCoordinates
from schemas.trip_context_schema import TravelStyle


class ChatIntent(str, Enum):
    RECOMMENDATION = "recommendation"
    COMPARISON = "comparison"
    INFORMATION = "information"
    CASUAL = "casual"


class ChatExecutionMode(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    QUALITY = "quality"
    AUTO = "auto"


class ChatContextRequest(BaseModel):
    language: str = Field(default="vi")
    address: str | None = None
    ref_id: str | None = None
    gps: GPSCoordinates | None = None

    check_in: datetime | None = None
    check_out: datetime | None = None
    min_price: int = Field(default=300000, ge=0)
    max_price: int = Field(default=3000000, ge=0)
    min_rating: float | None = Field(default=None, ge=0.0, le=5.0)
    required_amenities: list[str] = Field(default_factory=list, max_length=12)
    adults: int = Field(default=2, ge=1, le=10)
    children: list[int] | None = Field(default=None, max_length=6)

    personality: str = Field(default="can bang")
    trip_style: TravelStyle = TravelStyle.EXPLORE
    max_ranked_hotels: int = Field(default=5, ge=1, le=20)


class ChatAskRequest(BaseModel):
    message: str = Field(..., min_length=3, max_length=2000)
    context: ChatContextRequest | None = None
    history: list[str] = Field(default_factory=list, max_length=20)
    mode: ChatExecutionMode = ChatExecutionMode.BALANCED


class ChatRecommendationItem(BaseModel):
    name: str
    property_token: str | None = None
    price: float
    ai_score: float | None = None
    address: str | None = None
    reasons: list[str] = Field(default_factory=list)


class ChatCitation(BaseModel):
    source_type: str
    source_id: str | None = None
    title: str
    snippet: str


class ChatAskResponse(BaseModel):
    intent: ChatIntent
    message: str
    answer: str
    recommendations: list[ChatRecommendationItem] = Field(default_factory=list)
    citations: list[ChatCitation] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    requires_more_info: bool = False
    used_fallback: bool = False
