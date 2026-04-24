from core.exceptions import *
from schemas.discover_schema import DiscoverRequest, DiscoverHotel, WeatherInfo
from services.sentiment_service import sentiment_service
from services.summary_service import summary_service
from services.weather_service import weather_service
from services.hotel_ranking_service import hotel_ranking_service
from mock_data.virtual_review import virtual_review_manager
from externals.SerpAPI import serp_api
from externals.VietMapAPI import vietmap_api
from repositories.hotel_repo import hotel_repo
from loguru import logger
import asyncio

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
        )
        return result.data or []
      
    async def get_reviews(self, hotels: list[DiscoverHotel]):
        """Lấy review cho từng khách sạn"""
        for hotel in hotels:
            if len(hotel.user_reviews) > 0:
                continue

            virtual_review_manager.add_random_reviews(hotel, min_count=3, max_count=5)
        # XXX: hơi chậm
    
        
    async def execute_discover_pipeline(self) -> list[DiscoverHotel]:
        """Thực thi pipeline tìm kiếm"""
        gps_coordinates = None
        if self.payload.ref_id:
            # Nếu có ref_id, ưu tiên lấy GPS từ VietMap để có kết quả chính xác hơn
            place_detail = await vietmap_api.get_place_details(self.payload.ref_id)
            if place_detail and place_detail.result and place_detail.result.gps_coordinates:
                gps_coordinates = place_detail.result.gps_coordinates
                self.payload.address = place_detail.result.name
        else: # Tìm dựa trên address được nhập
            autocomplete_result = await vietmap_api.autocomplete(self.payload.address, self.payload.gps)
            if autocomplete_result and autocomplete_result.data:
                # Ko có gps ng dùng thì lấy cái đầu
                self.payload.address = autocomplete_result.data[0].display

                place_detail = await vietmap_api.get_place_details(autocomplete_result.data[0].ref_id)
                if place_detail and place_detail.result and place_detail.result.gps_coordinates:
                    gps_coordinates = place_detail.result.gps_coordinates # ưu tiên GPS từ autocomplete nếu có

        # Lấy trong database
        raw_results = await hotel_repo.search_hotels(gps_coordinates.latitude, gps_coordinates.longitude) if gps_coordinates else []
        # Dùng SerpAPI
        serpapi_results = await self.raw_search()
        
        hotel_dict: dict[str, DiscoverHotel] = {} # Gộp 2 kết quả
        for hotel in raw_results:
            if hotel.property_token:
                hotel_dict[hotel.property_token] = hotel

        for hotel in serpapi_results:
            if not hotel.property_token:
                continue
            
            if hotel.property_token not in hotel_dict: # Thêm mới
                hotel_dict[hotel.property_token] = hotel
            else: # Update thông tin mới cho property 
                db_hotel = hotel_dict[hotel.property_token]
                db_hotel.price = hotel.price
                db_hotel.deal = hotel.deal

        raw_results = list(hotel_dict.values())

        await self.get_reviews(raw_results)
        await self.sentiment_service.process_places_real_rating(raw_results)
        
        weather_by_identity: dict[str, list[WeatherInfo]] = {}
        try:
            destination_gps = gps_coordinates or self.payload.gps
            weather_by_identity = await weather_service.build_weather_context(
                raw_results,
                self.payload.check_in,
                self.payload.check_out,
                destination_gps=destination_gps,
            )
        except Exception as exc:
            logger.warning(f"Không xây dựng được weather context cho pipeline: {str(exc)}")

        raw_results = await hotel_ranking_service.rank_discovered_hotels(raw_results, self.payload, weather_by_identity=weather_by_identity, requester_username=self.requester_username)
        # await summary_service.process_places_ai_summary(raw_results, weather_by_identity=weather_by_identity) XXX: quá nghèo để có thể gọi AI Summary, tạm thời để sau
        # Chạy ngầm
        asyncio.create_task(
            hotel_repo.sync_hotels_background(raw_results) 
        )
        return raw_results