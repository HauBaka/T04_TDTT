from fastapi import APIRouter, Depends, HTTPException
from core.exceptions import AppException
from schemas.discover_schema import AddressSuggestionRequest, AddressSuggestionResponse, DiscoverRequest
from schemas.response_schema import ResponseSchema
from services.discover_service import DiscoverService

discover_router = APIRouter()

@discover_router.post("/discover", response_model=ResponseSchema)
async def perform(payload: DiscoverRequest):
    try:
        discover_service = DiscoverService(payload)
        results = await discover_service.execute_discover_pipeline()
        return ResponseSchema(data=results)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

# đề xuất, vd 5a nguyễn bỉnh khiêm -> 5a Đường Nguyễn Bỉnh Khiêm, Phường Đông Hòa, Thành Phố Dĩ An, Tỉnh Bình Dương
@discover_router.post("/discover/address-suggest", response_model=ResponseSchema[AddressSuggestionResponse])
async def suggest_address(query: AddressSuggestionRequest):
    return await DiscoverService.suggest_addresses(query)