from core.exceptions import *
from schemas.discover_schema import DiscoverRequest, DiscoverHotel
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
    async def hard_filter(self, raw_data: list[DiscoverHotel]) -> list[DiscoverHotel]:
        """Lọc dữ liệu thô theo các tiêu chí cứng"""
        return raw_data

    async def execute_discover_pipeline(self) -> list[DiscoverHotel]:
        """Thực thi pipeline tìm kiếm"""
        raw_results = await self.raw_search()
        filtered_results = await self.hard_filter(raw_results)
        # ...
        await hotel_repo.upsert_hotels(filtered_results)  # Lưu kết quả vào Firestore
        return filtered_results