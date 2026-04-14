from loguru import logger

from core.http_client import get_http_client
from core.settings import settings
from datetime import datetime, timedelta, timezone
from typing import Optional
from utils.beauty_json import list_to_str
from schemas.serpapi_schema import SerpAPIResultSchema
from schemas.discover_schema import DiscoverHotel, GPSCoordinates, HotelImage
import httpx
MAX_PRICE = 10000000

class SerpAPIClient:
    def __init__(self):
        self.api_key = settings.SERP_API_KEY
        self.account_url = "https://serpapi.com/account"
        self.hotel_search_url = "https://serpapi.com/search.json"
        self.reviews_search_url = "https://serpapi.com/search.json"

    async def get_status(self) -> dict:
        #print(self.api_key)
        if not self.api_key:
            return {"status": "missing API key"}
        
        client = get_http_client()
        try:
            response = await client.get(
                self.account_url, 
                params={"api_key": self.api_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                left = data.get("plan_searches_left")
                total = data.get("searches_per_month")

                if isinstance(left, int) and isinstance(total, int) and total > 0:
                    percent = left / total * 100
                    return {"status": f"connected ({percent:.2f}% available)"}

                return {"status": "connected (unknown quota)"}
                
            return {
                "status": "error: 401 - Invalid API Key" if response.status_code == 401 else f"error: HTTP {response.status_code} - {response.text}"
            }
        except httpx.RequestError as e:
            return {"status": f"error: network/request failed ({str(e)})"}
        
    def get_place_details(self, property_token: str) -> dict:
        return {"details": f"This is a mock details result for property_token {property_token} from SerpAPI."}
    async def search_places(
            self, 
            query: str,
            language: str = "vi", 
            currency: str = "VND", 
            check_in_date: Optional[str] = None, 
            check_out_date: Optional[str] = None,
            adults: int = 1, 
            children: Optional[list[int]] = None,
            min_price: int = 0,
            max_price: int = MAX_PRICE,
            next_page_token: Optional[str] = None
            ) -> SerpAPIResultSchema[list[DiscoverHotel]]:
        """
            Sử dụng SerpAPI để tìm kiếm khách sạn dựa trên các tham số đầu vào.\n
            Trả về kết quả đã được parse thành list[DiscoverHotel].
        """        

        # Nếu không có check-in/check-out, mặc định check-in là hôm nay và check-out là ngày mai
        now = datetime.now(timezone.utc)
        if check_in_date is None:
            check_in_date = now.strftime("%Y-%m-%d")
        if check_out_date is None:
            check_out_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        parameters = {
            "engine": "google_hotels",
            "api_key": self.api_key,
            "q": query,
            "hl": language,
            "gl": "VN",
            "currency": currency,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "min_price": min_price,
            "max_price": max_price,
        }

        if next_page_token:
            parameters["next_page_token"] = next_page_token

        if children:
            parameters["children"] = list_to_str(children)

        client = get_http_client()
        try:
            response = await client.get(
                self.hotel_search_url,
                params=parameters
            )
            # print(beauty_json(response.json()))  # In ra kết quả thô để debug 
            # Format lại clean hơn
            if response.status_code != 200:
                return SerpAPIResultSchema(
                    status_code=response.status_code,
                    message=f"error: HTTP {response.status_code} - {response.text}",
                    data=[]
                )
            
            data = response.json()
            parsed_hotels = []

            # Đổi từ dict sang DiscoverHotel
            for hotel in data.get("properties", []):
                try:
                        
                    # Tọa độ GPS
                    gps_coordinates = None
                    if "gps_coordinates" in hotel:
                        gps_coordinates = GPSCoordinates(
                            latitude=hotel["gps_coordinates"].get("latitude", 0.0),
                            longitude=hotel["gps_coordinates"].get("longitude", 0.0)
                        )

                    # images
                    images = []
                    if "images" in hotel:
                        for obj in hotel["images"]:
                            if not obj.get("thumbnail") or not obj.get("original_image"):
                                continue

                            HotelImageObj = HotelImage(
                                thumbnail=obj["thumbnail"],
                                original_image=obj["original_image"]
                            )
                            images.append(HotelImageObj)

                    hotel_obj = DiscoverHotel(
                        property_token=hotel.get("property_token"),
                        name = hotel.get("name", "Unknown Place"),
                        description = hotel.get("description"),
                        link = hotel.get("link"),
                        gps_coordinates= gps_coordinates,

                        check_in_time= hotel.get("check_in_time"),
                        check_out_time= hotel.get("check_out_time"),

                        price =  (hotel.get("rate_per_night") or {}).get("extracted_lowest", 0),
                        deal = hotel.get("deal"),

                        images=images,
                        amenities=hotel.get("amenities", []),

                        raw_rating= 0.0, # Dùng data ảo
                        user_reviews = []
                    )
                    parsed_hotels.append(hotel_obj)
                except Exception as e:
                    logger.warning(f"Error parsing hotel data: {str(e)} - Data: {hotel}")
                    continue
            return SerpAPIResultSchema(
                status_code=200,
                data=parsed_hotels,
                next_page_token=data.get("serpapi_pagination", {}).get("next_page_token")
            )

        except httpx.RequestError as e:
            return SerpAPIResultSchema(
                status_code=500,
                message=f"error: network/request failed ({str(e)})",
                data=[]
            )
    def search_reviews(
            self, 
            language: str = "vi", 
            property_token: str = ""
            ) -> dict:
        return {"reviews": "This is a mock reviews result from SerpAPI."}
serp_api = SerpAPIClient()