from fastapi import APIRouter, HTTPException

from core.exceptions import AppException
from schemas.discover_schema import (
    AddressSuggestionRequest,
    AddressSuggestionResponse,
    DiscoverHotel,
    DiscoverRequest,
    HotelSuggestionRequest,
)
from schemas.response_schema import GPSCoordinates, ResponseSchema
from services.discover_service import DiscoverService

discover_router = APIRouter()


@discover_router.post("/discover", response_model=ResponseSchema)
async def perform(payload: DiscoverRequest):
    """Tìm lodgings"""
    try:
        discover_service = DiscoverService(payload)
        results = await discover_service.execute_discover_pipeline()
        return ResponseSchema(data=results)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@discover_router.post(
    "/discover/address-suggest",
    response_model=ResponseSchema[AddressSuggestionResponse],
)
async def suggest_address(query: AddressSuggestionRequest):
    """Đề xuất địa chỉ dựa trên truy vấn đầu vào."""
    return await DiscoverService.suggest_addresses(query)


@discover_router.post(
    "/discover/hotels", response_model=ResponseSchema[list[DiscoverHotel]]
)
async def search_hotels(payload: HotelSuggestionRequest):
    """Tìm kiếm khách sạn dựa trên tên và vị trí (nếu có)"""
    return await DiscoverService.search_hotels(name=payload.name, gps=payload.gps)


@discover_router.get(
    "/discover/hotels/{hotel_id}", response_model=ResponseSchema[DiscoverHotel]
)
async def get_hotel_details(
    hotel_id: str, latitude: float | None = None, longitude: float | None = None
):
    """Lấy chi tiết khách sạn dựa trên hotel_id (property_token)"""
    gps = (
        GPSCoordinates(latitude=latitude, longitude=longitude)
        if latitude is not None and longitude is not None
        else None
    )
    return await DiscoverService.get_hotel_details(hotel_id=hotel_id, gps=gps)
