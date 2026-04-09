from core.exceptions import *
from schemas.discover_schema import DiscoverRequest, DiscoverHotel

class DiscoverService:
    def __init__(self, payload: DiscoverRequest):
        self.payload = payload

    async def raw_search(self) -> list[DiscoverHotel]:
        """Gọi SerpAPI để lấy dữ liệu thô dựa trên payload đầu vào"""
        return []
    async def hard_filter(self) -> list[DiscoverHotel]:
        """Lọc dữ liệu thô theo các tiêu chí cứng"""
        return []

    async def execute_discover_pipeline(self, payload: DiscoverRequest) -> list[DiscoverHotel]:
        """Thực thi pipeline tìm kiếm"""
        raw_results = await self.raw_search()
        filtered_results = await self.hard_filter()
        # ...
        return []