
from datetime import datetime, timezone
from core.exceptions import AppException, NotFoundError
from repositories.hotel_repo import hotel_repo
from schemas.response_schema import ResponseSchema
from schemas.response_schema import ResponseSchema
from schemas.trip_schema import TripCreateRequest, TripMemberInfo, TripResponse, TripStatus, TripUpdateRequest
from repositories.trip_repo import trip_repo
from repositories.user_repo import user_repo

class TripService:
    """Service xử lý logic nghiệp vụ liên quan đến Trip."""
    def __init__(self):
        self.trip_repo = trip_repo
        self.user_repo = user_repo
        
    async def create_trip(self, creator_uid: str, trip_data: TripCreateRequest) -> ResponseSchema[TripResponse]:
        """Tạo một trip mới."""
        creator_info = await self.user_repo.get_user(creator_uid)
        if not creator_info:
            raise NotFoundError("Creator user not found.")
        # Kiểm tra nếu creator đang tham gia trip khác
        if creator_info.get("current_trip"):
            raise AppException(status_code=400, message="You are already in a trip.")
        
        # Kiểm tra place_id hợp lệ
        if not await hotel_repo.valid_ids([trip_data.place_id]):
            raise AppException(status_code=400, message="Invalid place_id.")
        
        # Tạo trip mới
        new_trip = await self.trip_repo.create(creator_uid, trip_data.model_dump())
        if not new_trip:
            raise AppException(status_code=500, message="Failed to create trip.")
        
        trip_id = new_trip.get("id")
        if not trip_id:
            raise AppException(status_code = 500, message = "Trip ID is missing after creation.")

        updated_trip = await self.trip_repo.add_members(trip_id, [creator_uid])
        if not updated_trip:
            await self.trip_repo.delete(trip_id)  # Rollback: xóa trip nếu thêm owner thất bại
            raise AppException(status_code=500, message="Failed to add creator to trip.")
        
        await self.user_repo.update_user(creator_uid, {"current_trip": trip_id})
        
        return await self._build_trip_response(updated_trip)
    
    async def get_trip(self, trip_id: str, requester_uid: str | None) -> ResponseSchema[TripResponse]:
        """Lấy thông tin một trip theo ID."""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundError("Trip not found.")
        member_uids = await self._get_member_uids(trip)
        if requester_uid and requester_uid not in member_uids:
            raise AppException(status_code=403, message="You are not a member of this trip.")

        return await self._build_trip_response(trip)
    
    async def update_trip(self, trip_id: str, requester_uid: str, update_data: TripUpdateRequest) -> ResponseSchema[TripResponse]:
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundError("Trip not found.")

        if requester_uid != trip.get("owner_uid"):
            raise AppException(status_code=403, message="Only the trip owner can update this trip.")

        update_payload = update_data.model_dump(exclude_unset=True)
        new_status = update_payload.get("status")

        metadata_fields = {"name", "place_id", "start_at", "end_at"} # Metadata chỉ được sửa khi WAITING
        if update_payload.keys() & metadata_fields:
            if trip.get("status") != TripStatus.WAITING.value:
                raise AppException(
                    status_code=400,
                    message="Can only update trip details when status is WAITING."
                )

        # Kiểm tra rỗng
        if not update_payload:
            raise AppException(status_code=400, message="No valid fields provided for update.")

        # Kiểm tra place_id hợp lệ nếu có thay đổi
        if "place_id" in update_payload and not await hotel_repo.valid_ids([update_payload["place_id"]]):
            raise AppException(status_code=400, message="Invalid place_id.")

        # Update trip
        updated_trip = await self.trip_repo.update(trip_id, update_payload)
        if not updated_trip:
            raise AppException(status_code=500, message="Failed to update trip.")

        if new_status in (TripStatus.ENDED.value, TripStatus.ENDED):
            member_uids = await self._get_member_uids(trip)

            if member_uids:
                await self.user_repo.batch_update_current_trip(member_uids, None)

        return await self._build_trip_response(updated_trip)

    async def delete_trip(self, trip_id: str, requester_uid: str) -> ResponseSchema[bool]:
        """Xóa một trip."""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundError("Trip not found.")
        
        owner_uid = trip.get("owner_uid")
        if requester_uid != owner_uid:
            raise AppException(status_code=403, message="Only the trip owner can delete this trip.")
        
        member_uids = await self._get_member_uids(trip)
        if member_uids:
            await self.user_repo.batch_update_current_trip(member_uids, None)

        success = await self.trip_repo.delete(trip_id)
        if not success:
            raise AppException(status_code=500, message="Failed to delete trip.")
        return ResponseSchema(message="Trip deleted successfully", data=success)
    
    async def add_members_to_trip(self, trip_id: str, requester_uid: str, member_uids: list[str]) -> ResponseSchema[TripResponse]:
        """Thêm nhiều thành viên vào một trip."""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundError("Trip not found.")
        # Chỉ được phép thêm khi trip đang ở trạng thái WAITING
        trip_status = trip.get("status")
        if trip_status != TripStatus.WAITING.value:
            raise AppException(
                status_code=400, 
                message=f"Cannot add members. Trip is currently in '{trip_status}' status, expected 'waiting'."
            )
        # Chỉ member mới được thêm thành viên khác vào trip
        current_members = await self._get_member_uids(trip)
        if requester_uid not in current_members:
            raise AppException(status_code=403, message="You must be a member to add others.")
        # Loại bỏ những UID đã là member để tránh lỗi khi thêm trùng
        new_member_uids = [uid for uid in member_uids if uid not in current_members]
        if not new_member_uids:
            raise AppException(status_code=400, message="All members are already in this trip.")
        # Kiểm tra thông tin của các UID mới trước khi thêm
        users_info = await self.user_repo.get_users(new_member_uids)
        
        members_to_add = []
        for uid in new_member_uids:
            user_info = users_info.get(uid)
            if not user_info:
                raise NotFoundError(f"User {uid} not found in system.")
            
            # kiểm tra đảm bảo các user chuẩn bị thêm chưa tham gia trip nào khác
            if user_info.get("current_trip"):
                display_name = user_info.get("display_name", uid)
                raise AppException(status_code=400, message=f"User {display_name} is already in a trip.")   
            
            members_to_add.append(uid)

        updated_trip = await self.trip_repo.add_members(trip_id, members_to_add)
        
        if not updated_trip:
            raise AppException(status_code=500, message="Failed to add members to trip.")
        #Update: current_trip = trip_id cho các new member
        await self.user_repo.batch_update_current_trip(new_member_uids, trip_id)
        
        return await self._build_trip_response(updated_trip)
    
    async def remove_members_from_trip(self, trip_id: str, requester_uid: str, target_uids: list[str]) -> ResponseSchema[TripResponse]:
        """Xóa nhiều thành viên khỏi một trip."""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundError("Trip not found.")
        
        owner_uid = trip.get("owner_uid")
        current_members = await self._get_member_uids(trip)
        
        # Kiểm tra không xóa owner
        if owner_uid in target_uids:
            raise AppException(status_code=400, message="Cannot remove the trip owner.")
        
        # Kiểm tra tất cả target đều là member
        for uid in target_uids:
            if uid not in current_members:
                raise AppException(status_code=400, message=f"User {uid} is not a member of this trip.")
        
        # Kiểm tra quyền xóa
        is_owner = requester_uid == owner_uid
        
        if not is_owner:
            # Member thường chỉ có thể xóa chính mình
            if len(target_uids) != 1 or target_uids[0] != requester_uid:
                raise AppException(
                    status_code=403, 
                    message="You do not have permission to remove other members."
                )

        # Xóa member data từ subcollection
        updated_trip = await self.trip_repo.remove_members(trip_id, target_uids)
        
        if not updated_trip:
            raise AppException(status_code=500, message="Failed to remove members from trip.")
        # Update: current_trip = None cho các member bị xóa
        await self.user_repo.batch_update_current_trip(target_uids, None)
        return await self._build_trip_response(updated_trip)

    async def get_trip_members(self, trip_id: str, requester_uid: str) -> ResponseSchema[list[TripMemberInfo]]:
        """Lấy thông tin thành viên của một trip."""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundError("Trip not found.")
        
        # Chỉ member mới được xem danh sách thành viên
        members = await self.trip_repo.get_members(trip_id)
        current_members = [m["uid"] for m in members]
        if requester_uid not in current_members:
            raise AppException(
                status_code=403, 
                message="You must be a member of this trip to view its members."
            )
        
        members_info = [TripMemberInfo(**member) for member in members]

        return ResponseSchema(data=members_info)

    async def _build_trip_response(self, trip_data: dict) -> ResponseSchema[TripResponse]:
        """Hàm tiện ích để xây dựng TripResponse với thông tin member chi tiết."""
        if not trip_data:
            raise NotFoundError("Trip not found.")

        now = datetime.now(timezone.utc)
        return ResponseSchema(data=TripResponse(
            id=trip_data["id"],
            owner_uid=trip_data["owner_uid"],
            name=trip_data["name"],
            place_id=trip_data["place_id"],
            start_at=trip_data["start_at"],
            end_at=trip_data["end_at"],
            status=trip_data.get("status", TripStatus.WAITING.value),
            members=[TripMemberInfo(uid=m["uid"], joined_at=m["joined_at"]) for m in trip_data.get("members", [])],
            created_at=trip_data.get("created_at", now),
            updated_at=trip_data.get("updated_at", now)
        ))
    
    async def _get_member_uids(self, trip_data: dict) -> list[str]:
        """Hàm tiện ích để lấy danh sách UID thành viên của một trip."""
        if "members" in trip_data:
            return [m["uid"] for m in trip_data["members"]]
        
        members = await self.trip_repo.get_members(trip_data["id"])
        trip_data["members"] = members  # Cache lại để tránh gọi repo nhiều lần
        return [m["uid"] for m in members]

trip_service = TripService()
