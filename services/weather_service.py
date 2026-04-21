import asyncio
import logging
from schemas.discover_schema import DiscoverHotel, WeatherInfo
from externals.WeatherOpenMeteo import weather_open_meteo
from datetime import datetime, timedelta
from services.hotel_ranking_service import hotel_ranking_service
logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.weather_api = weather_open_meteo

    async def get_weather(self, lat: float, lng: float, from_date: str | None = None, to_date: str | None = None) -> list[WeatherInfo]:
        # Nếu không có from_date hoặc to_date, mặc định lấy weather cho 3 ngày từ hôm nay.
        if from_date is None or to_date is None:
            now = datetime.now()
            # Lấy ngày hôm nay
            from_date = now.strftime("%Y-%m-%d")
            # Cộng thêm 2 ngày nữa (Hôm nay + Ngày mai + Ngày mốt = 3 ngày)
            to_date = (now + timedelta(days=2)).strftime("%Y-%m-%d")
        elif not from_date:
            from_date=datetime.now().strftime("%Y-%m-%d")
        elif not to_date:
            to_date=(datetime.strptime(from_date, "%Y-%m-%d") + timedelta(days=2)).strftime("%Y-%m-%d")
        return await self.weather_api.search(lat, lng, from_date, to_date)

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
    
    async def build_weather_context(self, places: list[DiscoverHotel], check_in_date: datetime, check_out_date: datetime) -> dict[str, list[WeatherInfo]]:
        """
        Lấy thông tin thời tiết cho từng khách sạn trong danh sách places dựa trên tọa độ GPS của khách sạn.
        Nếu có khách sạn nào không lấy được weather riêng, sẽ dùng weather mặc định của vùng tìm kiếm.
        """
        # Format lại theo "YYYY-MM-DD"
        from_date = check_in_date.strftime("%Y-%m-%d")
        to_date = check_out_date.strftime("%Y-%m-%d")

        weather_tasks = []
        hotels_with_gps = []
        for hotel in places:
            if hotel.gps_coordinates is None:
                continue

            hotels_with_gps.append(hotel)
            weather_tasks.append(
                self.get_weather(
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

            if not isinstance(weather, list):
                logger.warning(f"Kết quả weather không hợp lệ cho {hotel.name}: {weather}")
                continue

            weather_key = hotel_ranking_service._hotel_weather_key(hotel)
            weather_by_identity[weather_key] = weather

            # Dùng weather thành công đầu tiên làm mặc định cho địa chỉ tìm kiếm.
            if default_weather is None:
                default_weather = weather

        # Hotel nào thiếu weather riêng sẽ nhận weather mặc định của vùng tìm kiếm.
        if default_weather is not None:
            for hotel in places:
                weather_key = hotel_ranking_service._hotel_weather_key(hotel)
                weather_by_identity.setdefault(weather_key, default_weather)

        return weather_by_identity

weather_service = WeatherService()