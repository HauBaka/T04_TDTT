from loguru import logger

from core.cache import cache_get, cache_key, cache_set
from core.exceptions import AppException, NotFoundError
from externals.SerpAPI import serp_api
from externals.VietMapAPI import vietmap_api
from mock_data.virtual_review import virtual_review_manager
from repositories.hotel_repo import hotel_repo
from schemas.discover_schema import (
    AddressSuggestion,
    AddressSuggestionRequest,
    AddressSuggestionResponse,
    DiscoverHotel,
    DiscoverRequest,
    DiscoverResponse,
)
from schemas.response_schema import GPSCoordinates, ResponseSchema

# from services.hotel_ranking_service import hotel_ranking_service
from schemas.vietmap_schema import AutoCompleteResult
from services.sentiment_service import sentiment_service
from utils.haversine_distance import haversine_distance

# from services.weather_service import weather_service


class DiscoverService:
    def __init__(self, payload: DiscoverRequest, requester_uid: str | None = None):
        self.payload = payload
        self.requester_uid = requester_uid
        self.sentiment_service = sentiment_service
        self.searching_place: AutoCompleteResult | None = None

    async def raw_search(self) -> list[DiscoverHotel]:
        """Gọi SerpAPI để lấy dữ liệu thô dựa trên payload đầu vào"""
        result = await serp_api.search_places(
            query=self.payload.address,
            check_in_date=self.payload.check_in.strftime("%Y-%m-%d"),
            check_out_date=self.payload.check_out.strftime("%Y-%m-%d"),
            adults=self.payload.adults,
            children=self.payload.children,
        )
        return result.data or []

    async def get_reviews(self, hotels: list[DiscoverHotel]):
        """Lấy review cho từng khách sạn"""
        for hotel in hotels:
            if len(hotel.user_reviews) > 0:
                continue

            virtual_review_manager.add_random_reviews(hotel, min_count=3, max_count=5)
        # XXX: hơi chậm

    async def execute_discover_pipeline(self) -> DiscoverResponse:
        """Thực thi pipeline tìm kiếm"""
        key = self._build_cache_key()
        cache_response = await self._get_from_cache()
        if cache_response:
            return cache_response

        gps_coordinates = None
        if self.payload.ref_id:
            # Nếu có ref_id, ưu tiên lấy GPS từ VietMap để có kết quả chính xác hơn
            place_detail = await vietmap_api.get_place_details(self.payload.ref_id)
            if (
                place_detail
                and place_detail.result
                and place_detail.result.gps_coordinates
            ):
                gps_coordinates = place_detail.result.gps_coordinates
                self.payload.address = place_detail.result.name
        else:  # Tìm dựa trên address được nhập
            autocomplete_result = await vietmap_api.autocomplete(
                self.payload.address, self.payload.gps
            )
            if autocomplete_result and autocomplete_result.data:
                # Ko có gps ng dùng thì lấy cái đầu
                self.payload.address = autocomplete_result.data[0].display
                self.searching_place = autocomplete_result.data[0]

                place_detail = await vietmap_api.get_place_details(
                    autocomplete_result.data[0].ref_id
                )
                if (
                    place_detail
                    and place_detail.result
                    and place_detail.result.gps_coordinates
                ):
                    gps_coordinates = (
                        place_detail.result.gps_coordinates
                    )  # ưu tiên GPS từ autocomplete nếu có

        # Lấy trong database
        raw_results = (
            await hotel_repo.search_hotels(
                gps_coordinates.latitude, gps_coordinates.longitude
            )
            if gps_coordinates
            else []
        )
        # Dùng SerpAPI
        serpapi_results = await self.raw_search()

        hotel_dict: dict[str, DiscoverHotel] = {}  # Gộp 2 kết quả
        for hotel in raw_results:
            if hotel.property_token:
                hotel_dict[hotel.property_token] = hotel

        for hotel in serpapi_results:
            if not hotel.property_token:
                continue

            if hotel.property_token not in hotel_dict:  # Thêm mới
                hotel_dict[hotel.property_token] = hotel
            else:  # Update thông tin mới cho property
                db_hotel = hotel_dict[hotel.property_token]
                db_hotel.price = hotel.price
                db_hotel.deal = hotel.deal

        raw_results = list(hotel_dict.values())

        await self.get_reviews(raw_results)
        await self.sentiment_service.process_places_real_rating(raw_results)

        # weather_by_identity: dict[str, list[WeatherInfo]] = {}
        # try:
        #     destination_gps = gps_coordinates or self.payload.gps
        #     weather_by_identity = await weather_service.build_weather_context(
        #         raw_results,
        #         self.payload.check_in,
        #         self.payload.check_out,
        #         destination_gps=destination_gps,
        #     )
        # except Exception as exc:
        #     logger.warning(
        #         f"Không xây dựng được weather context cho pipeline: {str(exc)}"
        #     )

        # raw_results = await hotel_ranking_service.rank_discovered_hotels(
        #     raw_results,
        #     self.payload,
        #     weather_by_identity=weather_by_identity,
        #     requester_uid=self.requester_uid,
        # )
        # await summary_service.process_places_ai_summary(raw_results, weather_by_identity=weather_by_identity) XXX: quá nghèo để có thể gọi AI Summary, tạm thời để sau
        # Chạy ngầm

        # await asyncio.gather(
        #     # hotel_repo.sync_hotels_background(raw_results),
        #     self._detail_searching_place(),
        #     self._calculate_distance_for_results(raw_results),
        # )

        await self._detail_searching_place()
        await self._calculate_distance_for_results(raw_results)

        # Cache the result
        result = DiscoverResponse(searching_place=self.searching_place, data=raw_results)
        
        await cache_set(key, DiscoverResponse(searching_place=self.searching_place, data=raw_results))

        return result

    @staticmethod
    async def suggest_addresses(
        query: AddressSuggestionRequest,
    ) -> ResponseSchema[AddressSuggestionResponse]:
        """Gợi ý địa chỉ dựa trên query đầu vào"""
        try:
            autocomplete_result = await vietmap_api.autocomplete(query.query, query.gps)
            if not autocomplete_result or not autocomplete_result.data:
                return ResponseSchema[AddressSuggestionResponse](
                    data=AddressSuggestionResponse(suggestions=[])
                )

            suggestions = []
            for item in autocomplete_result.data:
                suggestion = AddressSuggestion(
                    address=item.address,
                    name=item.name,
                    display=item.display,
                    distance=item.distance,
                    ref_id=item.ref_id,
                )
                suggestions.append(suggestion)
            return ResponseSchema[AddressSuggestionResponse](
                data=AddressSuggestionResponse(suggestions=suggestions)
            )
        except Exception as exc:
            logger.error(f"Error in suggest_addresses: {str(exc)}")
            raise AppException("Failed to get address suggestions", status_code=500)

    @staticmethod
    async def search_hotels(
        name: str, gps: GPSCoordinates | None = None
    ) -> ResponseSchema[list[DiscoverHotel]]:
        """Tìm kiếm khách sạn dựa trên tên và vị trí (nếu có)"""
        hotel_docs = await hotel_repo.search_hotels_by_name(name)
        hotels = []
        for hotel_doc in hotel_docs:
            try:
                hotel = DiscoverHotel.from_hotel_document(hotel_doc)
                if gps and hotel.gps_coordinates:
                    hotel.distance = haversine_distance(gps, hotel.gps_coordinates)
                hotels.append(hotel)
            except Exception as e:
                logger.error(
                    f"Error validating hotel data for document {hotel_doc.property_token}: {str(e)}"
                )

        return ResponseSchema(data=hotels)

    @staticmethod
    async def get_hotel_details(
        hotel_id: str, gps: GPSCoordinates | None = None
    ) -> ResponseSchema[DiscoverHotel]:
        """Lấy chi tiết khách sạn dựa trên hotel_id (property_token)"""
        hotel_doc = await hotel_repo.get_hotels([hotel_id])
        hotel = hotel_doc.get(hotel_id) if hotel_doc else None
        if not hotel:
            raise NotFoundError("Hotel not found")

        hotel_detail = DiscoverHotel.from_hotel_document(hotel)
        if gps and hotel_detail.gps_coordinates:
            hotel_detail.distance = haversine_distance(
                gps, hotel_detail.gps_coordinates
            )

        return ResponseSchema(data=hotel_detail)

    async def _detail_searching_place(self):
        if self.searching_place and self.searching_place.ref_id:
            try:
                place_detail = await vietmap_api.get_place_details(
                    self.searching_place.ref_id
                )

                if place_detail and place_detail.result:
                    self.searching_place = AutoCompleteResult(
                        name=place_detail.result.name,
                        address=place_detail.result.address,
                        display=place_detail.result.display,
                        ref_id=self.searching_place.ref_id,
                        distance=self.searching_place.distance,
                        gps=place_detail.result.gps_coordinates,
                    )

            except Exception as exc:
                logger.error(
                    f"Error in detail_searching_place "
                    f"for ref_id {self.searching_place.ref_id}: {exc}"
                )

    async def _calculate_distance_for_results(self, hotels: list[DiscoverHotel]):
        """Tính khoảng cách từ searching_place đến từng hotel

        Thuật toán sử dụng: Haversine để tính khoảng cách địa lý giữa 2 điểm GPS. Kết quả sẽ được lưu vào trường `distance` của từng hotel.
        """
        if not self.searching_place or not self.searching_place.gps:
            return

        for hotel in hotels:
            if hotel.gps_coordinates:
                hotel.distance = haversine_distance(
                    GPSCoordinates(
                        latitude=self.searching_place.gps.latitude,
                        longitude=self.searching_place.gps.longitude,
                    ),
                    hotel.gps_coordinates,
                )

    def _build_cache_key(self) -> str:
        """Xây dựng cache key dựa trên payload đầu vào"""
        return cache_key(
            "discover",
            self.payload.address or "",
            str(self.payload.check_in),
            str(self.payload.check_out),
            str(self.payload.adults),
            str(self.payload.children),
            str(self.payload.ref_id or ""),
        )

    async def _get_from_cache(self) -> DiscoverResponse | None:
        """Thử lấy kết quả từ cache dựa trên payload đầu vào"""
        key = self._build_cache_key()

        cached = await cache_get(key)
        if cached:
            try:
                return DiscoverResponse.model_validate(cached)
            except Exception as exc:
                logger.warning(f"Failed to parse cached discover response: {cached}, error: {str(exc)}")
                return None
        
        return None