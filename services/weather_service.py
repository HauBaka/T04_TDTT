import logging
from schemas.discover_schema import DiscoverHotel, GPSCoordinates, WeatherInfo
from externals.WeatherOpenMeteo import weather_open_meteo
from datetime import datetime
from services.hotel_ranking_service import hotel_ranking_service
from core.cache import cache_get, cache_set, cache_key
logger = logging.getLogger(__name__)

WEATHER_TTL_SECONDS = 3600

class WeatherService:
    def __init__(self):
        self.weather_api = weather_open_meteo

    async def get_weather(self, lat: float, lng: float, from_date: str, to_date: str) -> list[WeatherInfo]:
        # Cố gắng lấy từ cache trước
        cache_key_str = cache_key("weather", f"{lat:.4f}", f"{lng:.4f}", from_date, to_date)
        cached = await cache_get(cache_key_str)
        if cached:
            results = []
            for item in cached:
                try:
                    results.append(WeatherInfo.model_validate(item))
                except Exception as exc:
                    logger.warning(f"Failed to parse cached weather item: {item}, error: {str(exc)}")

            if results:
                return results

        result = await self.weather_api.search(lat, lng, from_date, to_date)
        await cache_set(cache_key_str, [w.model_dump(mode="python") for w in result], WEATHER_TTL_SECONDS)

        return result

    def get_weather_alert_flags(self, daily_weathers: list[WeatherInfo]) -> list[str]:
        flags = set()
        for w in daily_weathers:
            if w.rain_chance >= 80:
                flags.add("⚠️ Có khả năng mưa rất lớn hoặc bão.")
            elif w.rain_chance >= 50:
                flags.add("🌧️ Có thể có mưa rào, nhớ mang theo ô/dù.")
            
            if w.temp_c >= 35.0:
                flags.add("🥵 Nắng nóng gay gắt, chú ý chống nắng.")
            elif w.temp_c <= 15.0:
                flags.add("🥶 Thời tiết khá lạnh, cần mang theo áo ấm.")
        return list(flags)

    def summarize_trip_weather(self, daily_weathers: list[WeatherInfo]) -> str:

        if not daily_weathers:
            return "Chưa có thông tin dự báo thời tiết."
            
        avg_temp = sum(w.temp_c for w in daily_weathers) / len(daily_weathers)
        max_rain = max(w.rain_chance for w in daily_weathers)
        
        unique_conditions = list(dict.fromkeys([w.condition for w in daily_weathers]))
        condition_text = ", ".join(unique_conditions)
        
        summary = f"Trạng thái chung: {condition_text}. Nhiệt độ trung bình khoảng {avg_temp:.1f}°C."
        
        if max_rain > 70:
            summary += " Sẽ có ngày mưa lớn, bạn nên ưu tiên các hoạt động trong nhà."
        elif max_rain < 30:
            summary += " Thời tiết khô ráo, rất lý tưởng để du lịch và di chuyển."
        else:
            summary += " Trời có thể có mưa rải rác, bạn nên mang theo ô/dù phòng hờ khi ra ngoài."
            
        return summary
    
    async def build_weather_context(
        self,
        places: list[DiscoverHotel],
        check_in_date: datetime,
        check_out_date: datetime,
        destination_gps: GPSCoordinates | None = None,
    ) -> dict[str, list[WeatherInfo]]:
        """
        Lấy thông tin thời tiết 1 lần từ tọa độ vùng đi,
        sau đó gán cùng dữ liệu weather cho toàn bộ danh sách places.
        """
        # Format lại theo "YYYY-MM-DD"
        from_date = check_in_date.strftime("%Y-%m-%d")
        to_date = check_out_date.strftime("%Y-%m-%d")

        if destination_gps is None:
            logger.warning("Không có GPS điểm đến, không thể lấy weather.")
            return {}

        try:
            shared_weather = await self.get_weather(
                lat=destination_gps.latitude,
                lng=destination_gps.longitude,
                from_date=from_date,
                to_date=to_date,
            )
        except Exception as exc:
            logger.warning(f"Không lấy được weather theo vùng đi: {str(exc)}")
            return {}

        if not isinstance(shared_weather, list):
            logger.warning(f"Kết quả weather không hợp lệ theo vùng đi: {shared_weather}")
            return {}

        weather_by_identity: dict[str, list[WeatherInfo]] = {}
        for hotel in places:
            weather_key = hotel_ranking_service._hotel_weather_key(hotel)
            weather_by_identity[weather_key] = shared_weather

        return weather_by_identity

weather_service = WeatherService()