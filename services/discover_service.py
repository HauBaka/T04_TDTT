from core.exceptions import *
from schemas.discover_schema import DiscoverRequest, DiscoverHotel
from mock_data.virtual_review import virtual_review_manager
from externals.SerpAPI import serp_api
from repositories.hotel_repo import hotel_repo
class DiscoverService:
    def __init__(self, payload: DiscoverRequest):
        self.payload = payload

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
        # ...
        await hotel_repo.upsert_hotels(raw_results)  # Lưu kết quả vào Firestore
        return raw_results