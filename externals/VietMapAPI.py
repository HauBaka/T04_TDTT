from core.settings import settings
import httpx
from schemas.discover_schema import GPSCoordinates
from schemas.vietmap_schema import AutoCompleteResult, VietMapAutocompleteRequest, VietMapAutocompleteResponse, VietMapPlaceDetailRequest, VietMapPlaceDetailResponse, VietMapPlaceResult
import pygeohash as pgh

class VietMapAPI:
    def __init__(self):
        self.search_url = "https://maps.vietmap.vn/api/{type}/v4"
        self.api_key = settings.VIETMAP_API_KEY
        self.display_type = 6

    async def get_status(self) -> dict:
        """Kiểm tra trạng thái của API."""
        return {"status": "ok"}

    async def get_place_details(self, ref_id: str) -> VietMapPlaceDetailResponse:
        """Lấy chi tiết địa điểm dựa trên ref_id."""
        params = {
            "ref_id": ref_id,
            "apikey": self.api_key
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(self.search_url.format(type="place"), params=params)
            if response.status_code == 200:
                data = response.json()
                
                return VietMapPlaceDetailResponse(
                    result=VietMapPlaceResult(
                        name=data.get("name", ""),
                        gps_coordinates=GPSCoordinates(
                            latitude=data.get("gps_coordinates", {}).get("latitude", 0.0),
                            longitude=data.get("gps_coordinates", {}).get("longitude", 0.0),
                            geohash=pgh.encode(data.get("gps_coordinates", {}).get("latitude", 0.0), \
                                               data.get("gps_coordinates", {}).get("longitude", 0.0), \
                                                precision=5)
                        )
                    )
                )

        return VietMapPlaceDetailResponse(result=None)

    async def autocomplete(self, text: str, gps: GPSCoordinates | None = None) -> VietMapAutocompleteResponse:
        """Tìm kiếm thông tin địa điểm (đa dạng hơn hotel) dựa trên query."""
        params = {
            "text": text,
            "display_type": self.display_type,
            "apikey": self.api_key
        }
        if gps:
            params["focus"] = f"{gps.latitude},{gps.longitude}"

        async with httpx.AsyncClient() as client:
            response = await client.get(self.search_url.format(type="search"), params=params)
            if response.status_code == 200:
                data = response.json()

                results = []
                for item in data:
                    result = AutoCompleteResult(
                        name=item.get("name", ""),
                        address=item.get("address", ""),
                        display=item.get("display", ""),
                        ref_id=item.get("ref_id", ""),
                        distance=item.get("distance", None)
                    )
                    results.append(result)

                return VietMapAutocompleteResponse(data=results)

        return VietMapAutocompleteResponse(data=[])

vietmap_api = VietMapAPI()