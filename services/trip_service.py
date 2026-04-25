
from datetime import datetime

from schemas.response_schema import ResponseSchema
from schemas.trip_schema import TripCreateRequest, TripResponse, TripStatus, TripUpdateRequest


class TripService:
    """Service xử lý logic nghiệp vụ liên quan đến Trip."""
    
    async def create_trip(self, creator_uid: str, trip_data: TripCreateRequest) -> ResponseSchema[TripResponse]:
        """Tạo một trip mới."""
        return ResponseSchema(data=TripResponse(
            id="",
            owner_uid="",
            name="",
            place_id="",
            start_at=datetime.now(),
            end_at=datetime.now(),
            status=TripStatus.WAITING,
            member_uids=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        ))
    
    async def get_trip(self, trip_id: str, requester_uid: str | None) -> ResponseSchema[TripResponse]:
        """Lấy thông tin một trip theo ID."""
        return ResponseSchema(data=TripResponse(
            id=trip_id,
            owner_uid="owner_uid",
            name="Sample Trip",
            place_id="sample_place_id",
            start_at=datetime.now(),
            end_at=datetime.now(),
            status=TripStatus.ACTIVE,
            member_uids=["uid1", "uid2"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        ))
    
    async def update_trip(self, trip_id: str, requester_uid: str, update_data: TripUpdateRequest) -> ResponseSchema[TripResponse]:
        """Cập nhật thông tin một trip."""
        return ResponseSchema(data=TripResponse(
            id=trip_id,
            owner_uid="owner_uid",
            name="Sample Trip",
            place_id="sample_place_id",
            start_at=datetime.now(),
            end_at=datetime.now(),
            status=TripStatus.ACTIVE,
            member_uids=["uid1", "uid2"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        ))
    
    async def delete_trip(self, trip_id: str, requester_uid: str) -> ResponseSchema[bool]:
        """Xóa một trip."""
        return ResponseSchema(data=True)
    
    async def add_members_to_trip(self, trip_id: str, requester_uid: str, member_uids: list[str]) -> ResponseSchema[TripResponse]:
        """Thêm nhiều thành viên vào một trip."""
        return ResponseSchema(data=TripResponse(
            id=trip_id,
            owner_uid="owner_uid",
            name="Sample Trip",
            place_id="sample_place_id",
            start_at=datetime.now(),
            end_at=datetime.now(),
            status=TripStatus.ACTIVE,
            member_uids=["uid1", "uid2"] + member_uids,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ))
    
    async def remove_members_from_trip(self, trip_id: str, requester_uid: str, target_uids: list[str]) -> ResponseSchema[TripResponse]:
        """Xóa nhiều thành viên khỏi một trip."""
        existing_members = ["uid1", "uid2", "uid3"]  # Giả sử đây là danh sách thành viên hiện tại
        updated_members = [uid for uid in existing_members if uid not in target_uids]
        return ResponseSchema(data=TripResponse(
            id=trip_id,
            owner_uid="owner_uid",
            name="Sample Trip",
            place_id="sample_place_id",
            start_at=datetime.now(),
            end_at=datetime.now(),
            status=TripStatus.ACTIVE,
            member_uids=updated_members,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ))
    
trip_service = TripService()