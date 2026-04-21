from fastapi import APIRouter
from core.exceptions import AppException
from services.auth_service import AuthenticationService
from schemas.auth_schema import AuthRequest, AuthResponse
from schemas.response_schema import ResponseSchema

auth_router = APIRouter()

@auth_router.post("/auth", response_model=ResponseSchema[AuthResponse])
async def authenticate(auth_request: AuthRequest):
    auth_service = AuthenticationService(auth_request.token)
    return await auth_service.authenticate_user()