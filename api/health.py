from fastapi import APIRouter
from schemas.response_schema import ResponseSchema
from services.health_service import healthService

health_router = APIRouter()

@health_router.get("/health", response_model=ResponseSchema)
async def health_check():
    return ResponseSchema(data=healthService.info())
