from fastapi import APIRouter, Depends
from schemas.response_schema import ResponseSchema
from core.dependencies import get_current_user
from services.trip_service import trip_service
from schemas.trip_schema import TripCreateRequest, TripResponse, TripUpdateRequest,TripAddMembersRequest,TripRemoveMembersRequest

trip_router = APIRouter()

@trip_router.post("/trips", response_model=ResponseSchema[TripResponse])
async def create_trip(trip_request: TripCreateRequest, requester=Depends(get_current_user(optional=False))):
    """Tạo một trip mới cho người dùng đã xác thực."""
    return await trip_service.create_trip(requester.get("uid"), trip_request)

@trip_router.get("/trips/{trip_id}", response_model=ResponseSchema[TripResponse])
async def get_trip(trip_id: str, requester=Depends(get_current_user(optional=True))):
    """Lấy thông tin của một trip."""
    return await trip_service.get_trip(trip_id, requester.get("uid") if requester else None)

@trip_router.patch("/trips/{trip_id}", response_model=ResponseSchema[TripResponse])
async def update_trip(trip_id: str, trip_request: TripUpdateRequest, requester=Depends(get_current_user(optional=False))):
    """Cập nhật thông tin của một trip."""
    return await trip_service.update_trip(trip_id, requester.get("uid"), trip_request)

@trip_router.delete("/trips/{trip_id}", response_model=ResponseSchema[bool])
async def delete_trip(trip_id: str, requester=Depends(get_current_user(optional=False))):
    """Xóa một trip."""
    return await trip_service.delete_trip(trip_id, requester.get("uid"))

@trip_router.post("/trips/{trip_id}/members", response_model=ResponseSchema[TripResponse])
async def add_members_to_trip(trip_id: str, request: TripAddMembersRequest, requester=Depends(get_current_user(optional=False))):
    """Thêm nhiều thành viên vào một trip."""
    return await trip_service.add_members_to_trip(trip_id, requester.get("uid"), request.member_uids)

@trip_router.delete("/trips/{trip_id}/members", response_model=ResponseSchema[TripResponse])
async def remove_members_from_trip(trip_id: str, request: TripRemoveMembersRequest, requester=Depends(get_current_user(optional=False))):
    """Xóa nhiều thành viên khỏi một trip."""
    return await trip_service.remove_members_from_trip(trip_id, requester.get("uid"), request.target_uids)

