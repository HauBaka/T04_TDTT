from fastapi import APIRouter, Depends

from core.dependencies import get_current_user
from schemas.response_schema import ResponseSchema
from schemas.upload_schema import (
    UploadConfirmRequest,
    UploadConfirmResponse,
    UploadPresignRequest,
    UploadPresignResponse,
)
from services.upload_service import UploadService

upload_router = APIRouter(prefix="/uploads", tags=["uploads"])


@upload_router.post("/presign", response_model=ResponseSchema[UploadPresignResponse])
async def create_presigned_upload(
    request: UploadPresignRequest, user=Depends(get_current_user(optional=False))
):
    service = UploadService(user_id=user.get("uid"))
    result = await service.create_presigned_upload(request)

    return ResponseSchema(
        status_code=200,
        message="Presigned upload created",
        data=result,
    )


@upload_router.post("/confirm", response_model=ResponseSchema[UploadConfirmResponse])
async def confirm_upload(
    request: UploadConfirmRequest, user=Depends(get_current_user(optional=False))
):
    service = UploadService(user_id=user.get("uid"))
    result = await service.confirm_upload(request)

    return ResponseSchema(
        status_code=200,
        message="Upload confirmed",
        data=result,
    )
