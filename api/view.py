from fastapi import APIRouter, BackgroundTasks, Depends, Request

from core.dependencies import get_current_user
from schemas.response_schema import ResponseSchema
from schemas.view_schema import AddViewRequest, TopViewRequest
from services.view_service import view_service

view_router = APIRouter()


@view_router.post("/views", response_model=ResponseSchema)
async def add_view(
    request: Request,
    data: AddViewRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user(optional=True)),
):
    authorized = current_user is not None
    if current_user:
        viewer_id = current_user["uid"]
    else:
        forwarded_for = request.headers.get("X-Forwarded-For")
        viewer_id = (
            forwarded_for.split(",")[0].strip()
            if forwarded_for
            else request.client.host
            if request.client
            else "anonymous"
        )

    await view_service.add_view(
        viewer_id, authorized, data.target_id, data.target_type, background_tasks
    )
    return ResponseSchema(message="View added successfully")


@view_router.get("/views/top", response_model=ResponseSchema)
async def get_top_views(
    data: TopViewRequest = Depends(),
    current_user=Depends(get_current_user(optional=True)),
):
    top_views = await view_service.get_top_views(data)
    return ResponseSchema(data=top_views)
