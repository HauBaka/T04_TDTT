from schemas.discover_schema import WeatherInfo

class WeatherOpenMeteo:
    def __init__(self):
        self.search_url = "..."

    async def search(self, queries: dict) -> WeatherInfo:
        """Tìm kiếm thông tin thời tiết dựa trên query."""
        return {}
    
weather_open_meteo = WeatherOpenMeteo()