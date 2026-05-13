from fastapi import APIRouter, Depends

from core.dependencies import get_current_user
from schemas.response_schema import ResponseSchema

hotel_router = APIRouter()


@hotel_router.get("/hotels/{place_id}", response_model=ResponseSchema[None])
async def get_hotel_by_id(
    place_id: str, requester=Depends(get_current_user(optional=True))
):
    """Lấy thông tin chi tiết khách sạn dựa trên place_id."""
