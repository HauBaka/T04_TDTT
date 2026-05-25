import httpx
import pygeohash as pgh
from loguru import logger

from core.settings import settings
from schemas.discover_schema import GPSCoordinates
from schemas.vietmap_schema import (
    AutoCompleteResult,
    VietMapAutocompleteResponse,
    VietMapPlaceDetailResponse,
    VietMapPlaceResult,
)


class VietMapAPI:
    def __init__(self):
        self.search_url = "https://maps.vietmap.vn/api/{type}/v4"
        self.api_key = settings.VIETMAP_API_KEY.get_secret_value()
        self.display_type = 6
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0), headers={"Accept": "application/json"}
        )

    async def get_status(self) -> dict:
        """Kiểm tra trạng thái của API."""
        return {"status": "ok"}

    async def get_place_details(self, ref_id: str) -> VietMapPlaceDetailResponse:
        """Lấy chi tiết địa điểm dựa trên ref_id."""
        params = {"refid": ref_id, "apikey": self.api_key}

        try:
            response = await self.client.get(
                self.search_url.format(type="place"), params=params
            )

            if response.status_code == 200:
                data = response.json()
                return VietMapPlaceDetailResponse(
                    result=VietMapPlaceResult(
                        name=data.get("name", ""),
                        address=data.get("address", ""),
                        display=data.get("display", ""),
                        gps_coordinates=GPSCoordinates(
                            latitude=data.get("lat", 0.0),
                            longitude=data.get("lng", 0.0),
                            geohash=pgh.encode(
                                data.get("lat", 0.0),
                                data.get("lng", 0.0),
                                settings.GEOHASH_PRECISION,
                            ),
                        ),
                    )
                )

            logger.warning(
                f"Failed to get place details from VietMap for ref_id {ref_id}: HTTP {response.status_code} - {response.text}"
            )
        except httpx.ReadTimeout:
            logger.error(f"VietMap timeout for ref_id={ref_id}")
        except Exception as e:
            logger.exception(f"Unexpected VietMap error for ref_id={ref_id}: {e}")
        return VietMapPlaceDetailResponse(result=None)

    async def autocomplete(
        self, text: str, gps: GPSCoordinates | None = None
    ) -> VietMapAutocompleteResponse:
        """Tìm kiếm thông tin địa điểm (đa dạng hơn hotel) dựa trên query."""
        params = {
            "text": text,
            "display_type": self.display_type,
            "apikey": self.api_key,
        }
        if gps:
            params["focus"] = f"{gps.latitude},{gps.longitude}"

        try:
            response = await self.client.get(
                self.search_url.format(type="autocomplete"), params=params
            )

            if response.status_code == 200:
                data = response.json()

                results = []
                for item in data:
                    result = AutoCompleteResult(
                        name=item.get("name", ""),
                        address=item.get("address", ""),
                        display=item.get("display", ""),
                        ref_id=item.get("ref_id", ""),
                        distance=item.get("distance", -1.0),
                    )
                    results.append(result)

                return VietMapAutocompleteResponse(data=results)

            logger.warning(
                f"VietMap autocomplete failed for text={text}: "
                f"HTTP {response.status_code} - {response.text}"
            )
        except httpx.ReadTimeout:
            logger.error(f"VietMap timeout for text={text}")
        except Exception as e:
            logger.exception(f"Unexpected VietMap error for text={text}: {e}")
        return VietMapAutocompleteResponse(data=[])


vietmap_api = VietMapAPI()
