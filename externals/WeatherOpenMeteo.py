import httpx
import logging
from schemas.discover_schema import WeatherInfo

logger = logging.getLogger(__name__)

# Từ điển dịch mã thời tiết WMO sang Tiếng Việt
WMO_WEATHER_CODES = {
    0: "Trời quang mây, nắng đẹp",
    1: "Chủ yếu là nắng",
    2: "Nhiều mây",
    3: "Trời âm u",
    45: "Có sương mù",
    48: "Sương mù đóng băng",
    51: "Mưa phùn nhẹ",
    53: "Mưa phùn rải rác",
    55: "Mưa phùn dày hạt",
    61: "Mưa rào nhẹ",
    63: "Mưa vừa",
    65: "Mưa to",
    71: "Tuyết rơi nhẹ",
    80: "Mưa rào nhẹ từng cơn",
    81: "Mưa rào từng cơn",
    82: "Mưa rào xối xả",
    95: "Mưa dông, có sấm sét",
    96: "Mưa dông kèm mưa đá nhẹ",
    99: "Mưa dông kèm mưa đá to"
}

class WeatherOpenMeteo:
    def __init__(self):
        # Dùng để lấy thời tiết từ Tọa độ
        self.forecast_url = "https://api.open-meteo.com/v1/forecast"

    def _get_condition_text(self, code: int) -> str:
        """Hàm phụ trợ dịch mã WMO"""
        return WMO_WEATHER_CODES.get(code, "Thời tiết không xác định")

    async def search(self, lat: float, lng: float, start_date: str, end_date: str) -> list[WeatherInfo]:
        """Gọi API Open-Meteo lấy dữ liệu thô và ép kiểu sang Schema"""
        params = {
            "latitude": lat,
            "longitude": lng,
            "daily": "weather_code,temperature_2m_max,precipitation_probability_max",
            "timezone": "Asia/Ho_Chi_Minh",
            "start_date": start_date,
            "end_date": end_date
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.forecast_url, params=params)
                response.raise_for_status()
                data = response.json().get("daily", {})

                if not data or "time" not in data:
                    return []

                weather_list = []
                for i in range(len(data["time"])):
                    weather_list.append(
                        WeatherInfo(
                            condition=self._get_condition_text(data["weather_code"][i]),
                            temp_c=float(data["temperature_2m_max"][i]),
                            rain_chance=int(data["precipitation_probability_max"][i])
                        )
                    )
                return weather_list
            except Exception as e:
                logger.error(f"Lỗi gọi API Open-Meteo: {str(e)}")
                return []

weather_open_meteo = WeatherOpenMeteo()