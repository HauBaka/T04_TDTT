import logging
from schemas.discover_schema import WeatherInfo
from externals.WeatherOpenMeteo import weather_open_meteo
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.weather_api = weather_open_meteo

    async def get_weather(self, lat: float, lng: float, from_date: str=None, to_date: str=None) -> list[WeatherInfo]:
        if not from_date and not to_date:
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