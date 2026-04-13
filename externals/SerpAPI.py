from core.settings import settings
import time
import requests
from typing import Optional

MAX_PRICE = 10000000

class SerpAPIClient:
    def __init__(self):
        self.api_key = settings.SERP_API_KEY
        self.account_url = "https://serpapi.com/account"
        self.hotel_search_url = "https://serpapi.com/search.json"
        self.reviews_search_url = "https://serpapi.com/search.json"

    def get_status(self) -> dict:
        if not self.api_key:
            return {"status": "missing API key"}
        try:
            response = requests.get(
                self.account_url, 
                params={"api_key": self.api_key},
                timeout=5  # seconds
            )
            
            if response.status_code == 200:
                data = response.json()
                searches_left = data.get("plan_searches_left", "unknown")
                total_searches = data.get("searches_per_month", "unknown")
                return {"status": f"connected ({searches_left/total_searches * 100:.2f}% available)"}
                
            return {
                "status": "error: 401 - Invalid API Key" if response.status_code == 401 else f"error: HTTP {response.status_code} - {response.text}"
            }
        except requests.exceptions.RequestException as e:
            return {"status": f"error: network/request failed ({str(e)})"}
        
    def search_places(
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
            property_token: str = "",
            next_page_token: Optional[str] = None
            ) -> dict:
        if not self.api_key:
            return {"error": "missing API key"}

        if children is None:
            children = []

        if check_in_date is None:
            check_in_date = time.strftime("%Y-%m-%d")
        if check_out_date is None:
            check_out_date = time.strftime("%Y-%m-%d", time.localtime(time.time() + 86400))

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
            "children": children,
            "min_price": min_price,
            "max_price": max_price,
        }

        if next_page_token:
            parameters["next_page_token"] = next_page_token

        if children:
            parameters["children"] = ",".join(str(age) for age in children)

        if property_token and property_token.strip():
            parameters["property_token"] = property_token

        try:
            response = requests.get(
                self.hotel_search_url,
                params=parameters,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "results": data.get("properties", []),
                    "next_page_token": data.get("serpapi_pagination", {}).get("next_page_token")
                    }
            return {"error": f"HTTP {response.status_code} - {response.text}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"network/request failed ({str(e)})"}
    def search_reviews(
            self, 
            language: str = "vi", 
            property_token: str = ""
            ) -> dict:
        return {"reviews": "This is a mock reviews result from SerpAPI."}
serp_api = SerpAPIClient()