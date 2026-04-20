from core.exceptions import *
from schemas.discover_schema import DiscoverRequest, DiscoverHotel, WeatherInfo
from services.sentiment_service import sentiment_service
from services.summary_service import summary_service
from services.weather_service import weather_service
from services.hotel_ranking_service import hotel_ranking_service
from mock_data.virtual_review import virtual_review_manager
from externals.SerpAPI import serp_api
from repositories.hotel_repo import hotel_repo
from loguru import logger

class DiscoverService:
    def __init__(self, payload: DiscoverRequest, requester_username: str | None = None):
        self.payload = payload
        self.requester_username = requester_username
        self.sentiment_service = sentiment_service


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
    
        
    async def execute_discover_pipeline(self) -> list[DiscoverHotel]:
        """Thực thi pipeline tìm kiếm"""
        raw_results = await self.raw_search()
        await self.get_reviews(raw_results)
        await self.sentiment_service.process_places_real_rating(raw_results)
        
        weather_by_identity: dict[str, list[WeatherInfo]] = {}
        try:
            weather_by_identity = await weather_service.build_weather_context(raw_results, self.payload.check_in, self.payload.check_out)
        except Exception as exc:
            logger.warning(f"Không xây dựng được weather context cho pipeline: {str(exc)}")

        raw_results = await hotel_ranking_service.rank_discovered_hotels(raw_results, self.payload, weather_by_identity=weather_by_identity, requester_username=self.requester_username)
        # await summary_service.process_places_ai_summary(raw_results, weather_by_identity=weather_by_identity) XXX: quá nghèo để có thể gọi AI Summary, tạm thời để sau
        await hotel_repo.upsert_hotels(raw_results)  # Lưu kết quả vào Firestore
        return raw_results