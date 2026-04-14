from fastapi import APIRouter, HTTPException
from core.exceptions import AppException
from schemas.discover_schema import DiscoverRequest
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