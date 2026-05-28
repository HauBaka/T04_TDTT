from fastapi import APIRouter, Depends
from core.dependencies import get_current_user
from services.auth_service import AuthenticationService
from schemas.auth_schema import AuthResponse
from schemas.response_schema import ResponseSchema

auth_router = APIRouter()

@auth_router.post("/auth", response_model=ResponseSchema[AuthResponse])
async def authenticate(request = Depends(get_current_user(optional=False))):
    auth_service = AuthenticationService(request.get("uid"), request.get("email"))
    return await auth_service.authenticate_user()