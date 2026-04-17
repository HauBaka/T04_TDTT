from core.settings import settings
class VietMapAPI:
    def __init__(self):
        self.search_url = "..."
        self.api_key = settings.VIETMAP_API_KEY

    async def get_status(self) -> dict:
        """Kiểm tra trạng thái của API."""
        return {"status": "ok"}

    async def search(self, queries: dict) -> dict:
        """Tìm kiếm thông tin địa điểm dựa trên query."""
        return {}
    
vietmap_api = VietMapAPI()