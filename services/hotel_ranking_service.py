from __future__ import annotations

import math
import re
import asyncio
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from datetime import datetime, timezone
from typing import Iterable

from schemas.collection_schema import CollectionPublic
from schemas.discover_schema import DiscoverHotel, WeatherInfo
from schemas.hotel_ranking_schema import (
    HotelRankingItem,
    HotelRankingRequest,
    HotelRankingResponse,
)
from schemas.trip_context_schema import TripSearchCriteria, TravelStyle
from schemas.user_preference_schema import (
    ScoringWeights,
    UserBehaviorEvent,
    UserEventType,
    UserTravelPreference,
    WeatherTolerance,
)
from services.semantic_encoder import semantic_text_encoder

# Map tiếng anh sang tiếng việt (nếu đầu vào lỡ tiếng anh)
SINH_NGHIA_MAP = {
    "family room": "phong gia dinh",
    "family friendly": "phu hop gia dinh",
    "breakfast": "an sang",
    "pool": "ho boi",
    "kids": "tre em",
    "kids club": "cau lac bo tre em",
    "crib": "noi em be",
    "spa": "khu spa",
    "wifi": "wifi",
    "business center": "trung tam doanh nghiep",
    "desk": "ban lam viec",
    "meeting room": "phong hop",
    "quiet": "yen tinh",
    "laundry": "giat ui",
    "massage": "massage",
    "beach": "bai bien",
    "gym": "phong tap",
    "resort": "khu nghi duong",
    "sauna": "xong hoi",
    "island": "dao",
    "lake": "ho",
    "park": "cong vien",
    "mountain": "doi nui",
    "nature": "thien nhien",
    "viewpoint": "diem ngam",
    "attraction": "khu tham quan",
    "center": "trung tam",
    "downtown": "trung tam thanh pho",
    "old quarter": "pho co",
    "museum": "bao tang",
    "market": "cho",
    "restaurant": "nha hang",
    "bar": "quan bar",
    "indoor pool": "ho boi trong nha",
    "cafe": "quan cafe",
    "suite": "phong suite",
    "luxury": "sang trong",
    "valet": "dich vu do xe",
    "fine": "cao cap",
    "cheap": "gia re",
    "hostel": "nha nghi",
    "simple": "don gian",
    "budget": "tiet kiem",
    "tour": "tham quan",
    "view": "canh dep",
}

_NON_WORD_RE = re.compile(r"[^\w\s]+", flags=re.UNICODE)
_MULTI_SPACE_RE = re.compile(r"\s+")
_SINH_NGHIA_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (
        re.compile(rf"\b{re.escape(english_phrase)}\b", flags=re.UNICODE),
        vietnamese_phrase,
    )
    for english_phrase, vietnamese_phrase in sorted(
        SINH_NGHIA_MAP.items(), key=lambda item: len(item[0]), reverse=True
    )
)


@lru_cache(maxsize=4096)
def _strip_vietnamese_diacritics(text: str) -> str:
    if not text:
        return ""

    # NFKC để gom ký tự tương thích, casefold để lowercase chuẩn Unicode.
    normalized = unicodedata.normalize("NFKC", text).casefold()
    # Tiếng Việt có ký tự "đ" không bị loại khi bỏ dấu nên cần map thủ công.
    normalized = normalized.replace("đ", "d")

    decomposed = unicodedata.normalize("NFD", normalized)
    return "".join(
        char
        for char in decomposed
        if unicodedata.category(char) not in {"Mn", "Mc", "Me"}
    )

# hàm này để làm bình thường hóa text trước khi so sánh, giúp giảm thiểu sự khác biệt về cách diễn đạt (ví dụ: "phòng gia đình" vs "family room")
@lru_cache(maxsize=4096)
def normalize_text(text: str) -> str:
    if not text:
        return ""

    # Chuẩn hóa tiếng Việt có dấu/không dấu, rồi mới token hóa.
    without_tone = _strip_vietnamese_diacritics(text)
    cleaned = _NON_WORD_RE.sub(" ", without_tone)
    cleaned = _MULTI_SPACE_RE.sub(" ", cleaned).strip()

    for pattern, vietnamese_phrase in _SINH_NGHIA_PATTERNS:
        cleaned = pattern.sub(vietnamese_phrase, cleaned)

    return cleaned

# Tách text thành tokens sau khi đã được normalize, dùng để so sánh với các tập token của khách sạn, bộ sưu tập, sự kiện lịch sử,..
@lru_cache(maxsize=4096)
def tokenize_text(text: str) -> tuple[str, ...]:
    normalized = normalize_text(text)
    if not normalized:
        return tuple()
    return tuple(normalized.split())

# Lớp lưu trữ các tín hiệu liên quan đến khách sạn được sử dụng trong quá trình xếp hạng.
@dataclass(frozen=True)
class HotelSignal:
    """Precomputed hotel features used by multiple scorers."""
    hotel: DiscoverHotel
    identity: str
    feature_tokens: frozenset[str]
    location_tags: frozenset[str]
    amenity_tokens: frozenset[str]
    semantic_text: str

# Dịch vụ xếp hạng khách sạn dựa trên nhiều tín hiệu: đánh giá thực tế, sự phù hợp với hồ sơ người dùng, sự liên quan đến bộ sưu tập đã lưu, lịch sử tương tác, và sự phù hợp với điều kiện thời tiết dự kiến.
class HotelRankingService:
    SINH_NGHIA = SINH_NGHIA_MAP

    # Nhóm đồng nghĩa tiện ích ưu tiên cách gọi tiếng Việt.
    AMENITY_SYNONYMS: dict[str, set[str]] = {
        "wifi": {"wi fi", "mang", "mang khong day", "wifi mien phi", "internet"},
        "an sang": {"buffet sang", "bua sang", "diem tam", "an sang mien phi"},
        "ho boi": {"be boi", "ho boi ngoai troi", "ho boi trong nha"},
        "phong tap": {"phong gym", "khu tap", "trung tam the hinh"},
        "khu spa": {"spa", "thu gian", "cham soc suc khoe", "xong hoi", "massage"},
        "giat ui": {"dich vu giat ui", "giat la", "giat say"},
        "phong hop": {"phong hoi nghi", "phong su kien", "phong hop nho"},
        "phong suite": {"phong cao cap", "phong rong", "suite"},
        "dich vu do xe": {"bai do xe", "co cho de xe", "giu xe", "valet"},
        "gia dinh": {"phu hop gia dinh", "phong gia dinh", "co tre em"},
        "tre em": {"khu vui choi tre em", "cau lac bo tre em", "than thien voi tre em"},
    }

    TIEN_ICH_GIA_DINH = {"phong gia dinh", "phu hop gia dinh", "an sang", "ho boi", "tre em", "cau lac bo tre em", "noi em be", "khu spa"}
    TIEN_ICH_CONG_TAC = {"wifi", "trung tam doanh nghiep", "ban lam viec", "phong hop", "yen tinh", "giat ui"}
    TIEN_ICH_NGHI_DUONG = {"khu spa", "ho boi", "massage", "bai bien", "phong tap", "khu nghi duong", "xong hoi"}
    GOI_Y_DIEM_DEN = {"bai bien", "dao", "ho", "cong vien", "doi nui", "thien nhien", "diem ngam", "khu tham quan", "trung tam", "trung tam thanh pho", "pho co", "bao tang", "cho"}
    TIEN_ICH_TRONG_NHA = {"khu spa", "phong tap", "nha hang", "quan bar", "trung tam doanh nghiep", "giat ui", "ho boi trong nha", "phong hop", "quan cafe", "an sang"}
    
    # Trọng số mặc định cho từng loại sự kiện hành vi của người dùng, dùng để điều chỉnh điểm cá nhân hóa dựa trên mức độ tương tác.
    EVENT_WEIGHTS = {
        UserEventType.VIEW: 0.10,
        UserEventType.CLICK: 0.25,
        UserEventType.SAVE: 0.60,
        UserEventType.BOOK: 1.00,
        UserEventType.RATE: 0.75,
        UserEventType.REMOVE: -0.40,
    }
    
    # Tính chất chuyến đi của người dùng
    STYLE_LABELS = {
        TravelStyle.RELAX: "nghỉ dưỡng",
        TravelStyle.FAMILY: "gia đình",
        TravelStyle.WORK: "công tác",
        TravelStyle.EXPLORE: "khám phá",
        TravelStyle.ROMANTIC: "lãng mạn",
        TravelStyle.LUXURY: "sang trọng",
        TravelStyle.BUDGET: "tiết kiệm",
    }

    # Khởi tạo bộ xếp hạng và gắn bộ encode ngữ nghĩa.
    def __init__(self):
        self.semantic_encoder = semantic_text_encoder
        self._amenity_alias_index = self._build_alias_index(self.AMENITY_SYNONYMS)
        
    # Xếp hạng khách sạn bất đồng bộ để không chặn event loop.
    async def rank_hotels(self, request: HotelRankingRequest) -> HotelRankingResponse:
        ranked_hotels = await asyncio.to_thread(self._rank_hotels_sync, request)
        return HotelRankingResponse(ranked_hotels=ranked_hotels)
    
    # Chạy xếp hạng chính trong thread riêng và trả về danh sách đã sắp thứ tự.
    def _rank_hotels_sync(self, request: HotelRankingRequest) -> list[HotelRankingItem]:
        if not request.hotels:
            return []

        representative_weather = next(iter(request.weather_by_identity.values()), None)
        weights = self._resolve_weights(request.weights, request.profile, request.trip_criteria, request.collections, request.history, representative_weather)
        ranked_hotels: list[HotelRankingItem] = []

        for hotel in request.hotels:
            signal = self._build_hotel_signal(hotel)
            hotel_weather = request.weather_by_identity.get(self._hotel_weather_key(signal.hotel))
            component_scores = self._score_hotel(signal, request.profile, request.trip_criteria, request.collections, request.history, hotel_weather, weights)
            final_score = self._combine_scores(component_scores, weights)
            ranked_hotels.append(
                HotelRankingItem(
                    hotel=signal.hotel,
                    score=round(final_score, 4),
                    rank=0,
                )
            )

        ranked_hotels.sort(key=lambda item: item.score, reverse=True)
        ranked_hotels = ranked_hotels[: max(1, request.limit)]

        for index, item in enumerate(ranked_hotels, start=1):
            item.rank = index

        return ranked_hotels
    
    # Tự cân lại trọng số theo dữ liệu đầu vào của request.
    def _resolve_weights(
        self,
        user_weights: ScoringWeights | None,
        profile: UserTravelPreference,
        trip_criteria: TripSearchCriteria | None,
        collections: list[CollectionPublic],
        history: list[UserBehaviorEvent],
        weather: list[WeatherInfo] | None,
    ) -> ScoringWeights:
        if user_weights:
            return self._normalize_weights(user_weights)

        weights = ScoringWeights()

        if collections:
            weights.collection_affinity += min(0.10, 0.01 * len(collections))
            weights.profile_match -= min(0.05, 0.005 * len(collections))

        if history:
            weights.history_affinity += min(0.15, 0.01 * len(history))
            weights.profile_match -= min(0.05, 0.003 * len(history))

        if weather:
            severity = self._weather_severity(weather, profile)
            weights.weather_fit += min(0.10, severity * 0.10)
            weights.real_rating -= min(0.05, severity * 0.04)

        if not collections:
            weights.profile_match += 0.05
            weights.collection_affinity -= 0.03

        if not history:
            weights.profile_match += 0.05
            weights.history_affinity -= 0.03

        if profile.notes:
            weights.profile_match += 0.03

        if trip_criteria is not None:
            if trip_criteria.budget_min is not None or trip_criteria.budget_max is not None:
                weights.trip_match += 0.08
            if trip_criteria.trip_style is not None:
                weights.trip_match += 0.08
            if trip_criteria.party_size is not None:
                weights.trip_match += 0.04

        if trip_criteria is None:
            weights.trip_match -= 0.10

        return self._normalize_weights(weights)
    
    # Chuẩn hóa trọng số để tổng luôn bằng 1.
    def _normalize_weights(self, weights: ScoringWeights) -> ScoringWeights:
        weights = ScoringWeights(
            real_rating=max(0.0, weights.real_rating),
            profile_match=max(0.0, weights.profile_match),
            trip_match=max(0.0, weights.trip_match),
            collection_affinity=max(0.0, weights.collection_affinity),
            history_affinity=max(0.0, weights.history_affinity),
            weather_fit=max(0.0, weights.weather_fit),
        )
        total = weights.real_rating + weights.profile_match + weights.trip_match + weights.collection_affinity + weights.history_affinity + weights.weather_fit
        if total <= 0:
            return ScoringWeights()
        return ScoringWeights(
            real_rating=round(weights.real_rating / total, 4),
            profile_match=round(weights.profile_match / total, 4),
            trip_match=round(weights.trip_match / total, 4),
            collection_affinity=round(weights.collection_affinity / total, 4),
            history_affinity=round(weights.history_affinity / total, 4),
            weather_fit=round(weights.weather_fit / total, 4),
        )
        
    # Tính từng điểm thành phần trước khi ghép thành score cuối.
    def _score_hotel(
        self,
        signal: HotelSignal,
        profile: UserTravelPreference,
        trip_criteria: TripSearchCriteria | None,
        collections: list[CollectionPublic],
        history: list[UserBehaviorEvent],
        weather: list[WeatherInfo] | None,
        weights: ScoringWeights,
    ) -> dict[str, float]:
        real_rating = self._real_rating_score(signal.hotel)
        profile_match = self._profile_match_score(signal, profile)
        trip_match = self._trip_match_score(signal, trip_criteria)
        collection_affinity = self._collection_affinity_score(signal, collections)
        history_affinity = self._history_affinity_score(signal, history)
        weather_fit = self._weather_fit_score(signal, profile, weather)
        confidence = self._confidence_score(signal.hotel)

        return {
            "real_rating": real_rating,
            "profile_match": profile_match,
            "trip_match": trip_match,
            "collection_affinity": collection_affinity,
            "history_affinity": history_affinity,
            "weather_fit": weather_fit,
            "confidence": confidence,
        }
        
    # Ghép các điểm thành phần theo trọng số rồi nhân thêm độ tin cậy.
    def _combine_scores(self, component_scores: dict[str, float], weights: ScoringWeights) -> float:
        blended = (
            component_scores["real_rating"] * weights.real_rating
            + component_scores["profile_match"] * weights.profile_match
            + component_scores["trip_match"] * weights.trip_match
            + component_scores["collection_affinity"] * weights.collection_affinity
            + component_scores["history_affinity"] * weights.history_affinity
            + component_scores["weather_fit"] * weights.weather_fit
        )
        return self._clamp(blended * component_scores["confidence"], 0.0, 1.0)

    # Chấm điểm rating thực tế của khách sạn.
    def _real_rating_score(self, hotel: DiscoverHotel) -> float:
        if hotel.ai_score <= 0:
            return 0.5
        return self._clamp(hotel.ai_score / 5.0, 0.0, 1.0)
    
    # Chấm mức khớp giữa khách sạn và sở thích bền vững của người dùng.
    def _profile_match_score(
        self,
        signal: HotelSignal,
        profile: UserTravelPreference,
    ) -> float:
        score = 0.0
        total = 0.0

        semantic_score = self._semantic_similarity(self._profile_semantic_text(profile), signal.semantic_text)

        if profile.preferred_amenities:
            total += 1.0
            score += self._amenity_overlap_score(profile.preferred_amenities, signal.amenity_tokens)

        if profile.must_have_amenities:
            total += 1.0
            if self._amenity_contains_all(profile.must_have_amenities, signal.amenity_tokens):
                score += 1.0
            else:
                score += 0.15

        if profile.excluded_amenities:
            total += 1.0
            if self._amenity_contains_any(profile.excluded_amenities, signal.amenity_tokens):
                score += 0.1
            else:
                score += 1.0

        location_tags = signal.location_tags
        if profile.preferred_location_tags:
            total += 1.0
            score += self._keyword_overlap_score(profile.preferred_location_tags, list(location_tags))

        if profile.disliked_location_tags and self._contains_any(profile.disliked_location_tags, list(location_tags)):
            total += 1.0
            score += 0.2

        if profile.notes:
            total += 1.0
            score += self._free_text_match_score(profile.notes, signal.hotel)

        if total == 0:
            return semantic_score if semantic_score is not None else 0.5

        rule_score = self._clamp(score / total, 0.0, 1.0)
        return self._blend_rule_and_semantic(rule_score, semantic_score)

    # Chấm mức khớp theo tiêu chí của riêng chuyến đi.
    def _trip_match_score(self, signal: HotelSignal, trip_criteria: TripSearchCriteria | None) -> float:
        if trip_criteria is None:
            return 0.5

        score = 0.0
        total = 0.0
        semantic_score = self._semantic_similarity(self._trip_semantic_text(trip_criteria), signal.semantic_text)

        if trip_criteria.budget_min is not None and trip_criteria.budget_max is not None:
            total += 1.0
            score += self._budget_score(signal.hotel.price, trip_criteria.budget_min, trip_criteria.budget_max)

        if trip_criteria.trip_style is not None:
            total += 1.0
            score += self._trip_style_score(signal.hotel, trip_criteria.trip_style)

        if trip_criteria.party_size is not None:
            total += 1.0
            if trip_criteria.party_size <= 2:
                score += self._keyword_overlap_score({"phong suite", "lang man", "yen tinh"}, signal.feature_tokens)
            elif trip_criteria.party_size >= 4:
                score += self._keyword_overlap_score({"gia dinh", "tre em", "an sang", "khu nghi duong"}, signal.feature_tokens)
            else:
                score += 0.65

        if total == 0:
            return semantic_score if semantic_score is not None else 0.5

        rule_score = self._clamp(score / total, 0.0, 1.0)
        return self._blend_rule_and_semantic(rule_score, semantic_score)
    
    # Chấm mức hợp với bộ sưu tập đã lưu của người dùng.
    def _collection_affinity_score(self, signal: HotelSignal, collections: list[CollectionPublic]) -> float:
        if not collections:
            return 0.5

        scores: list[float] = []

        for collection in collections:
            collection_tokens = self._collection_tokens(collection)
            exact_match = any(self._normalize_token(place) == signal.identity for place in collection.places)
            if exact_match:
                scores.append(1.0)
                continue

            overlap = self._jaccard(collection_tokens, signal.feature_tokens)
            recency = self._recency_weight(collection.updated_at)
            scores.append(self._clamp(overlap * recency, 0.0, 1.0))

        if not scores:
            return self._semantic_similarity(self._collections_semantic_text(collections), signal.semantic_text) or 0.5

        rule_score = round(sum(scores) / len(scores), 4)
        semantic_score = self._semantic_similarity(self._collections_semantic_text(collections), signal.semantic_text)
        return self._blend_rule_and_semantic(rule_score, semantic_score)
    
    # Chấm mức hợp với lịch sử xem/lưu/đặt phòng trước đó.
    def _history_affinity_score(self, signal: HotelSignal, history: list[UserBehaviorEvent]) -> float:
        if not history:
            return 0.5

        # Positive/negative events are time-decayed and accumulated here.
        weighted_scores: list[float] = []

        for event in history:
            base_weight = self.EVENT_WEIGHTS.get(event.event_type, 0.0)
            if base_weight == 0.0:
                continue

            event_identity = self._normalize_token(event.hotel_id or event.hotel_name or "")
            if event_identity and event_identity == signal.identity:
                match_score = 1.0
            else:
                event_tokens = self._event_tokens(event)
                match_score = self._jaccard(event_tokens, signal.feature_tokens)
                if event.hotel_name and self._normalize_token(event.hotel_name) == self._normalize_token(signal.hotel.name):
                    match_score = max(match_score, 0.85)

            recency = self._recency_weight(event.created_at)
            adjusted = base_weight * match_score * recency
            weighted_scores.append(adjusted)

        if not weighted_scores:
            semantic_score = self._semantic_similarity(self._history_semantic_text(history), signal.semantic_text)
            return semantic_score if semantic_score is not None else 0.5

        average = sum(weighted_scores) / len(weighted_scores)
        rule_score = self._clamp(0.5 + average / 2.0, 0.0, 1.0)
        semantic_score = self._semantic_similarity(self._history_semantic_text(history), signal.semantic_text)
        return self._blend_rule_and_semantic(rule_score, semantic_score)
    
    # Chấm mức hợp với thời tiết dự kiến và sức chịu thời tiết của user.
    def _weather_fit_score(
        self,
        signal: HotelSignal,
        profile: UserTravelPreference,
        weather: list[WeatherInfo] | None,
    ) -> float:
        if not weather:
            return 0.5

        avg_temp = sum(item.temp_c for item in weather) / len(weather)
        max_rain = max(item.rain_chance for item in weather)
        hotel_tags = signal.feature_tokens
        indoor_support = len(hotel_tags.intersection(self.TIEN_ICH_TRONG_NHA))
        severity = self._weather_severity(weather, profile)

        if max_rain >= 80:
            base = 0.25 if profile.weather_tolerance == WeatherTolerance.LOW else 0.5 if profile.weather_tolerance == WeatherTolerance.MEDIUM else 0.7
            if indoor_support:
                base += min(0.2, 0.05 * indoor_support)
            return self._clamp(base, 0.0, 1.0)

        if avg_temp >= 35:
            base = 0.3 if profile.weather_tolerance == WeatherTolerance.LOW else 0.55 if profile.weather_tolerance == WeatherTolerance.MEDIUM else 0.75
            if self._contains_any({"ho boi", "khu spa"}, hotel_tags):
                base += 0.1
            return self._clamp(base, 0.0, 1.0)

        if max_rain >= 50:
            base = 0.5 if profile.weather_tolerance == WeatherTolerance.LOW else 0.7 if profile.weather_tolerance == WeatherTolerance.MEDIUM else 0.8
            if indoor_support:
                base += 0.1
            return self._clamp(base, 0.0, 1.0)

        if profile.weather_tolerance == WeatherTolerance.MEDIUM:
            base = 0.65
            if indoor_support:
                base += 0.05
            return self._clamp(base, 0.0, 1.0)

        return 0.7
    
    # Chấm độ tin cậy của dữ liệu đầu vào cho khách sạn.
    def _confidence_score(self, hotel: DiscoverHotel) -> float:
        review_density = min(1.0, len(hotel.analyzed_reviews) / 8.0)
        trust = self._clamp(hotel.trust_weight, 0.0, 1.0)
        if hotel.ai_score <= 0 and not hotel.analyzed_reviews:
            return 0.55
        return self._clamp(0.55 + 0.25 * trust + 0.20 * review_density, 0.0, 1.0)
    
    # Chấm điểm tinh chỉnh trong nhóm đã qua lọc budget.
    def _budget_score(self, price: float, budget_min: int, budget_max: int) -> float:
        if budget_min <= 0 and budget_max <= 0:
            return 0.5
        if budget_min <= price <= budget_max:
            return 1.0
        if price < budget_min:
            gap = budget_min - price
            return self._clamp(1.0 - (gap / max(budget_min, 1)) * 0.4, 0.0, 1.0)
        gap = price - budget_max
        return self._clamp(1.0 - (gap / max(budget_max, 1)) * 0.5, 0.0, 1.0)
    
    # Chấm mức hợp với phong cách chuyến đi.
    def _trip_style_score(self, hotel: DiscoverHotel, trip_style: TravelStyle) -> float:
        tokens = self._hotel_feature_tokens(hotel) | self._hotel_location_tags(hotel)

        style_map = {
            TravelStyle.FAMILY: self.TIEN_ICH_GIA_DINH | {"gia dinh", "tre em", "an sang"},
            TravelStyle.WORK: self.TIEN_ICH_CONG_TAC | {"trung tam", "doanh nghiep", "phong hop"},
            TravelStyle.RELAX: self.TIEN_ICH_NGHI_DUONG | {"khu nghi duong", "khu spa", "yen tinh"},
            TravelStyle.EXPLORE: self.GOI_Y_DIEM_DEN | {"tham quan", "kham pha", "diem den"},
            TravelStyle.ROMANTIC: {"khu spa", "yen tinh", "canh dep", "bai bien", "khu nghi duong", "ho boi"},
            TravelStyle.LUXURY: {"khu spa", "ho boi", "phong suite", "sang trong", "khu nghi duong", "dich vu do xe", "cao cap"},
            TravelStyle.BUDGET: {"tiet kiem", "gia re", "nha nghi", "don gian", "trung tam"},
        }

        expected = style_map.get(trip_style, set())
        if not expected:
            return 0.5
        return self._keyword_overlap_score(list(expected), list(tokens))
    
    # So khớp ghi chú tự do của user với khách sạn.
    def _free_text_match_score(self, note: str, hotel: DiscoverHotel) -> float:
        tokens = self._tokenize(note)
        hotel_tokens = self._hotel_feature_tokens(hotel)
        if not tokens:
            return 0.5
        return self._jaccard(tokens, hotel_tokens)
    
    def _hotel_feature_tokens(self, hotel: DiscoverHotel) -> set[str]:
        # Lấy token đặc trưng của khách sạn, không tính điểm gần đó.
        tokens = set(self._tokenize(hotel.name))
        tokens.update(self._tokenize(hotel.description or ""))
        tokens.update(self._tokenize(hotel.address or ""))
        tokens.update(self._tokenize(hotel.deal or ""))
        tokens.update(self._tokenize(" ".join(hotel.amenities)))
        return tokens

    def _hotel_location_tags(self, hotel: DiscoverHotel) -> set[str]:
        # Lấy tag vị trí từ địa chỉ và điểm gần đó.
        tags = set()
        for nearby_place in hotel.nearby_places:
            tags.update(self._tokenize(nearby_place.category or ""))
            tags.update(self._tokenize(nearby_place.name))
            tags.update(self._tokenize(nearby_place.description or ""))
        if hotel.address:
            tags.update(self._tokenize(hotel.address))
        return tags

    def _collection_tokens(self, collection: CollectionPublic) -> set[str]:
        # Lấy token đặc trưng từ bộ sưu tập.
        tokens = set(self._tokenize(collection.name))
        tokens.update(self._tokenize(collection.description or ""))
        tokens.update(self._tokenize(" ".join(collection.tags)))
        tokens.update(self._tokenize(" ".join(collection.places)))
        return tokens

    def _event_tokens(self, event: UserBehaviorEvent) -> set[str]:
        # Lấy token từ một sự kiện hành vi.
        tokens = set(self._tokenize(event.hotel_name or ""))
        tokens.update(self._tokenize(event.hotel_id or ""))
        tokens.update(self._tokenize(" ".join(event.metadata.values())))
        return tokens

    # Chuẩn hoá và mở rộng token tiện ích (có cả cụm từ + đồng nghĩa).
    def _amenity_tokens(self, amenities: list[str]) -> set[str]:
        tokens: set[str] = set()
        for amenity in amenities:
            normalized = self._normalize_token(amenity)
            if not normalized:
                continue
            tokens.add(normalized)
            words = [word for word in normalized.split() if word]
            tokens.update(words)
            for size in (2, 3):
                if len(words) >= size:
                    for index in range(len(words) - size + 1):
                        tokens.add(" ".join(words[index : index + size]))

        expanded = set(tokens)
        for token in list(tokens):
            expanded.update(self._expand_amenity_term(token))
        return expanded

    # Tính mức trùng khớp giữa hai tập từ khóa.
    def _keyword_overlap_score(self, keywords: list[str] | set[str], tokens: list[str] | set[str]) -> float:
        keyword_set = {self._normalize_token(item) for item in keywords if self._normalize_token(item)}
        token_set = {self._normalize_token(item) for item in tokens if self._normalize_token(item)}
        if not keyword_set:
            return 0.5
        overlap = len(keyword_set.intersection(token_set))
        return self._clamp(overlap / len(keyword_set), 0.0, 1.0)

    # Tính overlap tiện ích có xét đồng nghĩa/alias.
    def _amenity_overlap_score(self, amenities: Iterable[str], amenity_tokens: Iterable[str]) -> float:
        expanded_keywords = self._expand_amenity_terms(amenities)
        token_set = {self._normalize_token(item) for item in amenity_tokens if self._normalize_token(item)}
        if not expanded_keywords:
            return 0.5
        overlap = len(expanded_keywords.intersection(token_set))
        return self._clamp(overlap / len(expanded_keywords), 0.0, 1.0)

    # Kiểm tra tất cả tiện ích bắt buộc có xuất hiện theo nghĩa tương đương.
    def _amenity_contains_all(self, amenities: Iterable[str], amenity_tokens: Iterable[str]) -> bool:
        token_set = {self._normalize_token(item) for item in amenity_tokens if self._normalize_token(item)}
        for amenity in amenities:
            if not self._expand_amenity_term(amenity).intersection(token_set):
                return False
        return True

    # Kiểm tra có bất kỳ tiện ích loại trừ nào xuất hiện theo nghĩa tương đương.
    def _amenity_contains_any(self, amenities: Iterable[str], amenity_tokens: Iterable[str]) -> bool:
        token_set = {self._normalize_token(item) for item in amenity_tokens if self._normalize_token(item)}
        return bool(self._expand_amenity_terms(amenities).intersection(token_set))

    # Mở rộng danh sách tiện ích thành tập từ có đồng nghĩa.
    def _expand_amenity_terms(self, amenities: Iterable[str]) -> set[str]:
        expanded: set[str] = set()
        for amenity in amenities:
            expanded.update(self._expand_amenity_term(amenity))
        return expanded

    # Mở rộng một tiện ích đơn lẻ bằng alias index.
    def _expand_amenity_term(self, amenity: str) -> set[str]:
        normalized = self._normalize_token(amenity)
        if not normalized:
            return set()
        return set(self._amenity_alias_index.get(normalized, {normalized}))

    # Tạo chỉ mục alias hai chiều để tra theo canonical hoặc alias.
    def _build_alias_index(self, groups: dict[str, set[str]]) -> dict[str, set[str]]:
        alias_index: dict[str, set[str]] = {}
        for canonical, variants in groups.items():
            canonical_norm = self._normalize_token(canonical)
            variant_norms = {self._normalize_token(value) for value in variants if self._normalize_token(value)}
            combined = {canonical_norm, *variant_norms}
            for token in combined:
                alias_index[token] = set(combined)
        return alias_index

    # Kiểm tra source có đủ toàn bộ từ khóa hay không.
    def _contains_all(self, keywords: Iterable[str], source: Iterable[str]) -> bool:
        source_tokens = {self._normalize_token(item) for item in source}
        return all(self._normalize_token(item) in source_tokens for item in keywords)

    # Kiểm tra source có chứa ít nhất một từ khóa hay không.
    def _contains_any(self, keywords: Iterable[str], source: Iterable[str]) -> bool:
        source_tokens = {self._normalize_token(item) for item in source}
        return any(self._normalize_token(item) in source_tokens for item in keywords)

    # Tính Jaccard giữa hai tập token.
    def _jaccard(self, left: Iterable[str], right: Iterable[str]) -> float:
        left_set = {self._normalize_token(item) for item in left if self._normalize_token(item)}
        right_set = {self._normalize_token(item) for item in right if self._normalize_token(item)}
        if not left_set or not right_set:
            return 0.0
        union = left_set.union(right_set)
        intersection = left_set.intersection(right_set)
        return len(intersection) / len(union)
    
    # hàm này để làm gì?
    # Hàm này tính trọng số giảm dần theo thời gian cho các sự kiện hành vi của người dùng, để các tương tác gần đây có ảnh hưởng lớn hơn đến điểm lịch sử.
    def _recency_weight(self, when: datetime) -> float:
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        # Exponential decay: recent interactions matter more than old ones.
        age_days = max(0.0, (now - when).total_seconds() / 86400.0)
        return self._clamp(math.exp(-age_days / 180.0), 0.25, 1.0)

    # Ước lượng mức độ nặng của thời tiết.
    def _weather_severity(self, weather: list[WeatherInfo], profile: UserTravelPreference) -> float:
        if not weather:
            return 0.0
        avg_rain = sum(item.rain_chance for item in weather) / len(weather)
        avg_temp = sum(item.temp_c for item in weather) / len(weather)
        severity = 0.0
        if avg_rain >= 80:
            severity += 0.7
        elif avg_rain >= 50:
            severity += 0.4
        if avg_temp >= 35:
            severity += 0.4
        elif avg_temp <= 15:
            severity += 0.3

        if profile.weather_tolerance == WeatherTolerance.LOW:
            severity *= 1.15
        elif profile.weather_tolerance == WeatherTolerance.HIGH:
            severity *= 0.75
        return self._clamp(severity, 0.0, 1.0)

    # Tạo ID chuẩn hóa cho khách sạn.
    def _hotel_identity(self, hotel: DiscoverHotel) -> str:
        base = hotel.property_token or hotel.name
        return self._normalize_token(base)

    # Tạo key riêng cho weather mapping để tránh trùng identity giữa các khách sạn khác nhau.
    def _hotel_weather_key(self, hotel: DiscoverHotel) -> str:
        if hotel.property_token:
            return f"token:{self._normalize_token(hotel.property_token)}"

        lat_part = ""
        lng_part = ""
        if hotel.gps_coordinates is not None:
            lat_part = f"{hotel.gps_coordinates.latitude:.4f}"
            lng_part = f"{hotel.gps_coordinates.longitude:.4f}"

        return "|".join(
            [
                "name_addr",
                self._normalize_token(hotel.name),
                self._normalize_token(hotel.address or ""),
                lat_part,
                lng_part,
            ]
        )

    # Gom sẵn tín hiệu của khách sạn để tính điểm nhanh hơn.
    def _build_hotel_signal(self, hotel: DiscoverHotel) -> HotelSignal:
        feature_tokens = self._hotel_feature_tokens(hotel)
        location_tags = self._hotel_location_tags(hotel)
        identity = self._hotel_identity(hotel)

        return HotelSignal(
            hotel=hotel,
            identity=identity,
            feature_tokens=frozenset(feature_tokens),
            location_tags=frozenset(location_tags),
            amenity_tokens=frozenset(self._amenity_tokens(hotel.amenities)),
            semantic_text=self._hotel_semantic_text(hotel),
        )

    # Ghép text tổng hợp cho khách sạn.
    def _hotel_semantic_text(self, hotel: DiscoverHotel) -> str:
        parts = [
            f"ten_khach_san: {hotel.name}",
            f"mo_ta: {hotel.description or ''}",
            f"dia_chi: {hotel.address or ''}",
            f"tien_ich: {'; '.join(hotel.amenities)}",
            f"uu_dai: {hotel.deal or ''}",
            f"khu_vuc_lan_can: {'; '.join(place.name for place in hotel.nearby_places[:5])}",
        ]
        return " | ".join(part for part in parts if part)

    # Ghép text tổng hợp cho sở thích bền vững của user.
    def _profile_semantic_text(self, profile: UserTravelPreference) -> str:
        parts = [
            f"uu_tien_tien_ich: {'; '.join(profile.preferred_amenities)}",
            f"bat_buoc: {'; '.join(profile.must_have_amenities)}",
            f"khong_thich: {'; '.join(profile.excluded_amenities)}",
            f"uu_tien_vi_tri: {'; '.join(profile.preferred_location_tags)}",
            f"tranh_vi_tri: {'; '.join(profile.disliked_location_tags)}",
            f"nhay_cam_thoi_tiet: {profile.weather_tolerance.value}",
            f"ghi_chu: {profile.notes or ''}",
        ]
        return " | ".join(part for part in parts if part)

    # Ghép text tổng hợp cho tiêu chí chuyến đi.
    def _trip_semantic_text(self, trip_criteria: TripSearchCriteria) -> str:
        parts = [
            f"phong_cach_chuyen_di: {self._style_label(trip_criteria.trip_style)}",
            f"ngan_sach_tu: {trip_criteria.budget_min if trip_criteria.budget_min is not None else ''}",
            f"ngan_sach_den: {trip_criteria.budget_max if trip_criteria.budget_max is not None else ''}",
            f"so_nguoi: {trip_criteria.party_size if trip_criteria.party_size is not None else ''}",
        ]
        return " | ".join(part for part in parts if part)
    
    def _collections_semantic_text(self, collections: list[CollectionPublic]) -> str:
        # Ghép text từ các bộ sưu tập đã lưu.
        parts: list[str] = []
        for collection in collections[:10]:
            parts.append(f"ten_bo_suu_tap: {collection.name}")
            if collection.description:
                parts.append(f"mo_ta_bo_suu_tap: {collection.description}")
            if collection.tags:
                parts.append(f"tag: {'; '.join(collection.tags)}")
            if collection.places:
                parts.append(f"dia_diem_da_luu: {'; '.join(collection.places)}")
        return " | ".join(parts)

    def _history_semantic_text(self, history: list[UserBehaviorEvent]) -> str:
        # Ghép text từ lịch sử hành vi.
        parts: list[str] = []
        for event in history[:30]:
            parts.append(
                " | ".join(
                    piece
                    for piece in [
                        f"su_kien: {event.event_type.value}",
                        f"ten_khach_san: {event.hotel_name or ''}",
                        f"hotel_id: {event.hotel_id or ''}",
                        f"gia_tri: {event.value if event.value is not None else ''}",
                        f"ghi_chu: {'; '.join(event.metadata.values())}",
                    ]
                    if piece
                )
            )
        return " | ".join(parts)

    # So khớp ngữ nghĩa bằng embedding.
    def _semantic_similarity(self, left_text: str, right_text: str) -> float | None:
        if not left_text or not right_text:
            return None
        return self.semantic_encoder.similarity(left_text, right_text)

    # Trộn điểm rule với điểm ngữ nghĩa.
    def _blend_rule_and_semantic(self, rule_score: float, semantic_score: float | None) -> float:
        if semantic_score is None:
            return self._clamp(rule_score, 0.0, 1.0)
        return self._clamp((0.65 * rule_score) + (0.35 * semantic_score), 0.0, 1.0)

    # Bọc lại hàm tokenize cho gọn.
    def _tokenize(self, text: str) -> list[str]:
        return list(tokenize_text(text))

    # Bọc lại hàm normalize cho gọn.
    def _normalize_token(self, text: str) -> str:
        return normalize_text(text)

    # Giữ số nằm trong một khoảng.
    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    # Đổi enum phong cách chuyến đi sang nhãn dễ đọc.
    def _style_label(self, trip_style: TravelStyle) -> str:
        return self.STYLE_LABELS.get(trip_style, "chưa xác định")
