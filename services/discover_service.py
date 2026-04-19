from core.exceptions import *
from datetime import datetime, timezone, timedelta
from schemas.discover_schema import DiscoverRequest, DiscoverHotel, AIReviewSummary, WeatherInfo
from schemas.collection_schema import CollectionPublic
from schemas.hotel_ranking_schema import HotelRankingRequest
from schemas.trip_context_schema import TripSearchCriteria
from schemas.user_preference_schema import ScoringWeights, UserBehaviorEvent, UserTravelPreference
from services.sentiment_service import sentiment_service
from services.summary_service import SummaryService
from services.user_service import user_service
from services.weather_service import WeatherService
from services.hotel_ranking_service import HotelRankingService
from mock_data.virtual_review import virtual_review_manager
from externals.SerpAPI import serp_api
from repositories.hotel_repo import hotel_repo
import asyncio
from loguru import logger

REAL_RATING_CACHE_EXPIRATION_DAYS=7
SUMMARY_CACHE_EXPIRATION_DAYS = 14 

class DiscoverService:
    def __init__(self, payload: DiscoverRequest, requester_username: str | None = None):
        self.payload = payload
        self.requester_username = requester_username
        self.sentiment_service = sentiment_service
        self.summary_service = SummaryService()
        self.weather_service = WeatherService()
        self.hotel_ranking_service = HotelRankingService()

    async def _build_weather_context(self, places: list[DiscoverHotel]) -> dict[str, list[WeatherInfo]]:
        from_date = self.payload.check_in.strftime("%Y-%m-%d") if self.payload.check_in else None
        to_date = self.payload.check_out.strftime("%Y-%m-%d") if self.payload.check_out else None

        weather_tasks = []
        hotels_with_gps = []
        for hotel in places:
            if hotel.gps_coordinates is None:
                continue
            hotels_with_gps.append(hotel)
            weather_tasks.append(
                self.weather_service.get_weather(
                    lat=hotel.gps_coordinates.latitude,
                    lng=hotel.gps_coordinates.longitude,
                    from_date=from_date,
                    to_date=to_date,
                )
            )

        if not weather_tasks:
            return {}

        weather_results = await asyncio.gather(*weather_tasks, return_exceptions=True)

        weather_by_identity: dict[str, list[WeatherInfo]] = {}
        default_weather: list[WeatherInfo] | None = None

        for hotel, weather in zip(hotels_with_gps, weather_results):
            if isinstance(weather, Exception):
                logger.warning(f"Không lấy được weather cho {hotel.name}: {str(weather)}")
                continue
            if not weather:
                continue

            weather_key = self.hotel_ranking_service._hotel_weather_key(hotel)
            weather_by_identity[weather_key] = weather

            # Dùng weather thành công đầu tiên làm mặc định cho địa chỉ tìm kiếm.
            if default_weather is None:
                default_weather = weather

        # Hotel nào thiếu weather riêng sẽ nhận weather mặc định của vùng tìm kiếm.
        if default_weather is not None:
            for hotel in places:
                weather_key = self.hotel_ranking_service._hotel_weather_key(hotel)
                weather_by_identity.setdefault(weather_key, default_weather)

        return weather_by_identity


    async def raw_search(self) -> list[DiscoverHotel]:
        """Gọi SerpAPI để lấy dữ liệu thô dựa trên payload đầu vào"""
        result = await serp_api.search_places(
            query=self.payload.address,
            language=self.payload.language,
            check_in_date=self.payload.check_in.strftime("%Y-%m-%d"),
            check_out_date=self.payload.check_out.strftime("%Y-%m-%d"),
            adults=self.payload.adults,
            children=self.payload.children,
            min_price=self.payload.min_price,
            max_price=self.payload.max_price,
        )
        return result.data or []
      
    async def get_reviews(self, hotels: list[DiscoverHotel]):
        """Lấy review cho từng khách sạn"""
        for hotel in hotels:
            virtual_review_manager.add_random_reviews(hotel, min_count=25, max_count=50)
        # XXX: hơi chậm
        
    async def process_places_real_rating(self, filtered_places: list[DiscoverHotel]):
        """
        Xử lý điểm đánh giá thực tế cho từng khách sạn trong danh sách đã lọc. Cụ thể:
        Với mỗi khách sạn trong filtered_places, kiểm tra xem đã có điểm đánh giá thực tế (ai_score) và ngày hết hạn của điểm đó (ai_score_expiration_date):
            - Nếu có và còn hạn (cập nhật trong vòng 7 ngày), lấy điểm đánh giá thực tế
            - Nếu không có hoặc đã hết hạn, gọi SentimentService để tính điểm đánh giá thực tế mới dựa trên review gốc và phân tích cảm xúc
        """
        
        if not filtered_places or len(filtered_places) == 0:
            return
        
        sentiment_tasks = []
        places_needing_calculation = []
        now = datetime.now(timezone.utc)

        for place in filtered_places:
            expiration_date = place.ai_score_expiration_date # Sử dụng datetime để so sánh, tránh chuyển đổi qua lại giữa string và datetime
            has_cache = len(place.analyzed_reviews) > 0 # Đã có AI review chưa

            if has_cache and (expiration_date and now < expiration_date):
                # Nếu đã có ai review và còn hạn, thì không cần tính lại
                continue

            # Lấy raw_reviews (danh sách UserReview) từ object
            raw_reviews = place.user_reviews # luôn có trường này
            if not raw_reviews or len(raw_reviews) == 0:
                # Nếu không có review nào, không thể tính điểm đánh giá thực tế, gán mặc định để tránh lỗi
                place.ai_score = place.raw_rating 
                place.analyzed_reviews = []
                place.ai_score_expiration_date = now + timedelta(days=REAL_RATING_CACHE_EXPIRATION_DAYS)
                place.trust_weight = 0.0 # Không có review nào -> không đáng tin cậy
                continue

            # Đưa vào hàng đợi để gọi AI xử lí song song
            task = self.sentiment_service.calculate_real_rating(raw_reviews)
            sentiment_tasks.append(task)
            places_needing_calculation.append(place)

        # Thực thi tất cả các tác vụ AI cùng lúc
        if sentiment_tasks:
            results = await asyncio.gather(*sentiment_tasks, return_exceptions=True)
            new_expiration_date = now + timedelta(days=REAL_RATING_CACHE_EXPIRATION_DAYS) # Sử dụng datetime 
            # Cập nhật kết quả vào từng place tương ứng
            for place, result in zip(places_needing_calculation, results):
                if isinstance(result, BaseException):
                    # Nếu có lỗi khi gọi AI, gán mặc định tạm thời để tránh bị kẹt 7 ngày không có điểm đánh giá nào cả
                    place.ai_score = place.raw_rating  # Hoặc có thể gán một giá trị mặc định nào đó
                    place.analyzed_reviews = []
                    place.ai_score_expiration_date = now
                    place.trust_weight = 0.0
                    continue

                # Gán kết quả AI vào Place
                real_rating, trust_weight, analyzed_reviews = result
                place.ai_score = real_rating
                place.trust_weight = trust_weight
                place.analyzed_reviews = analyzed_reviews
                place.ai_score_expiration_date = new_expiration_date
    
    async def process_places_ai_summary(
        self,
        filtered_places: list[DiscoverHotel],
        weather_by_identity: dict[str, list[WeatherInfo]] | None = None,
    ):
        """
        Module này sẽ đảm nhiệm việc tạo tóm tắt AI cho từng khách sạn dựa trên review đã phân tích, tiện ích và vị trí lân cận. Cụ thể:
        Với mỗi khách sạn trong filtered_places, kiểm tra xem đã có tóm tắt AI (ai_summary) và ngày hết hạn của tóm tắt đó (ai_summary_expiration_date):
            - Nếu có và còn hạn (cập nhật trong vòng 14 ngày), lấy tóm tắt
            - Nếu không có hoặc đã hết hạn, gọi SummaryService để tạo tóm tắt mới dựa trên review đã phân tích, tiện ích và vị trí lân cận
        """
        
        if not filtered_places:
            return

        if weather_by_identity is None:
            weather_by_identity = await self._build_weather_context(filtered_places)

        ai_tasks = []
        places_needing_summary = []
        now = datetime.now(timezone.utc)

        for place in filtered_places:
            # Lấy dữ liệu cần thiết để gọi AI Summary
            user_reviews = place.analyzed_reviews 
            amenities = place.amenities
            nearby_places = place.nearby_places
            
            hotel_name = place.name 
            
            # 2. Kiểm tra đã có ai_summary và ai_summary_expiration_date chưa
            ai_summary = place.ai_summary
            expiration_date = place.ai_summary_expiration_date # Sử dụng datetime

            if ai_summary and expiration_date and now < expiration_date:
                # Nếu đã có tóm tắt và còn hạn, không cần gọi AI
                continue
            
            weather_key = self.hotel_ranking_service._hotel_weather_key(place)
            weather = weather_by_identity.get(weather_key, [])

            # Chuẩn bị luồng gọi AI nếu cần thiết
            # Tạo coroutine cho việc gọi AI Summary, nhưng chưa chạy ngay mà sẽ chạy cùng lúc ở bước sau để tối ưu hiệu suất
            task = self.summary_service.generate_places_summary(
                analyzed_reviews=user_reviews,
                hotel_name=hotel_name,
                amenities=amenities,
                nearby_places=nearby_places,
                weather=weather
            )
            ai_tasks.append(task)
            places_needing_summary.append(place)

        # Thực thi tất cả các tác vụ AI Summary cùng lúc
        if ai_tasks:
            # Chờ tất cả AI tasks chạy xong cùng lúc
            summaries_results = await asyncio.gather(*ai_tasks, return_exceptions=True)

            # Tính toán ngày hết hạn mới cho những place được update
            new_expiration_date = now + timedelta(days=SUMMARY_CACHE_EXPIRATION_DAYS)

            # Cập nhật kết quả AI vào từng place tương ứng
            for place, summary in zip(places_needing_summary, summaries_results):
                if isinstance(summary, Exception):
                    # Nếu Gemini lỗi, gán mặc định tạm thời để tránh bị kẹt 14 ngày không có tóm tắt nào cả
                    place.ai_summary = AIReviewSummary(
                        overview="Không thể tải tóm tắt tổng quan lúc này.",
                        pros=["Lỗi hệ thống khi tải tóm tắt ưu điểm."],
                        cons=["Lỗi hệ thống khi tải tóm tắt nhược điểm."],
                        notes="Không thể tổng hợp bằng AI lúc này."
                    )
                    # Đặt ngày hết hạn là thời điểm hiện tại (now) để lần tìm kiếm sau nó tự động gọi lại AI thay vì bị kẹt 14 ngày
                    place.ai_summary_expiration_date = now
                    continue

                # Cập nhật kết quả AI vào Place
                place.ai_summary = summary
                place.ai_summary_expiration_date = new_expiration_date
                
                
    async def rank_discovered_hotels(
        self,
        places: list[DiscoverHotel],
        weather_by_identity: dict[str, list[WeatherInfo]] | None = None,
    ) -> list[DiscoverHotel]:
        if not places:
            return places

        profile = UserTravelPreference()
        collections: list[CollectionPublic] = []
        history: list[UserBehaviorEvent] = []
        scoring_weights: ScoringWeights | None = None

        if self.requester_username:
            try:
                profile_response = await user_service.get_profile(
                    requester_token=None,
                    target_username=self.requester_username,
                )
                private_user = profile_response.user

                profile_data = getattr(private_user, "travel_profile", None)
                if isinstance(profile_data, UserTravelPreference):
                    profile = profile_data
                elif isinstance(profile_data, dict):
                    try:
                        profile = UserTravelPreference.model_validate(profile_data)
                    except Exception:
                        profile = UserTravelPreference()

                collection_data = getattr(private_user, "collections", [])
                if isinstance(collection_data, list):
                    parsed_collections: list[CollectionPublic] = []
                    for item in collection_data:
                        if isinstance(item, CollectionPublic):
                            parsed_collections.append(item)
                        elif isinstance(item, dict):
                            try:
                                parsed_collections.append(CollectionPublic.model_validate(item))
                            except Exception:
                                continue
                    collections = parsed_collections[:50]

                history_data = getattr(private_user, "user_behavior_history", [])
                if isinstance(history_data, list):
                    parsed_history: list[UserBehaviorEvent] = []
                    for event in history_data:
                        if isinstance(event, UserBehaviorEvent):
                            parsed_history.append(event)
                        elif isinstance(event, dict):
                            try:
                                parsed_history.append(UserBehaviorEvent.model_validate(event))
                            except Exception:
                                continue
                    history = parsed_history[:100]

                weight_data = getattr(private_user, "scoring_weights", None)
                if isinstance(weight_data, ScoringWeights):
                    scoring_weights = weight_data
                elif isinstance(weight_data, dict):
                    try:
                        scoring_weights = ScoringWeights.model_validate(weight_data)
                    except Exception:
                        scoring_weights = None
            except Exception as exc:
                logger.warning(f"Không tải được personalization context cho ranking: {str(exc)}")

        personality_note = (self.payload.personality or "").strip()
        if personality_note:
            existing_notes = (profile.notes or "").strip()
            profile.notes = f"{existing_notes}. {personality_note}" if existing_notes else personality_note

        # trip_criteria đã được chuẩn hoá và đồng bộ trong DiscoverRequest validator.
        trip_criteria = self.payload.trip_criteria.model_copy(deep=True) if self.payload.trip_criteria else TripSearchCriteria()

        if weather_by_identity is None:
            weather_by_identity = {}
            try:
                weather_by_identity = await self._build_weather_context(places)
            except Exception as exc:
                logger.warning(f"Không xây dựng được weather context cho ranking: {str(exc)}")

        hotel_ranking_request = HotelRankingRequest(
            hotels=places,
            profile=profile,
            trip_criteria=trip_criteria,
            weather_by_identity=weather_by_identity,
            collections=collections,
            history=history,
            weights=scoring_weights,
            limit=min(self.payload.max_ranked_hotels or len(places), len(places)),
        )

        ranked_response = await self.hotel_ranking_service.rank_hotels(hotel_ranking_request)
        return [item.hotel for item in ranked_response.ranked_hotels]
        
    async def execute_discover_pipeline(self) -> list[DiscoverHotel]:
        """Thực thi pipeline tìm kiếm"""
        raw_results = await self.raw_search()
        await self.get_reviews(raw_results)
        await self.process_places_real_rating(raw_results)
        weather_by_identity: dict[str, list[WeatherInfo]] = {}
        try:
            weather_by_identity = await self._build_weather_context(raw_results)
        except Exception as exc:
            logger.warning(f"Không xây dựng được weather context cho pipeline: {str(exc)}")

        raw_results = await self.rank_discovered_hotels(raw_results, weather_by_identity=weather_by_identity)
        # await self.process_places_ai_summary(raw_results, weather_by_identity=weather_by_identity) XXX: quá nghèo để có thể gọi AI Summary, tạm thời để sau
        await hotel_repo.upsert_hotels(raw_results)  # Lưu kết quả vào Firestore
        return raw_results