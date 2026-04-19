from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.collection_schema import CollectionPublic
from schemas.discover_schema import DiscoverHotel, WeatherInfo
from schemas.trip_context_schema import TripSearchCriteria
from schemas.user_preference_schema import (
    ScoringWeights,
    UserBehaviorEvent,
    UserTravelPreference,
)

class HotelRankingRequest(BaseModel):
    hotels: list[DiscoverHotel]
    profile: UserTravelPreference
    trip_criteria: TripSearchCriteria | None = None
    collections: list[CollectionPublic] = Field(default_factory=list)
    history: list[UserBehaviorEvent] = Field(default_factory=list)
    weather_by_identity: dict[str, list[WeatherInfo]] = Field(default_factory=dict)
    limit: int = 10
    weights: ScoringWeights | None = None


class HotelRankingItem(BaseModel):
    hotel: DiscoverHotel
    score: float
    rank: int


class HotelRankingResponse(BaseModel):
    ranked_hotels: list[HotelRankingItem] = Field(default_factory=list)
