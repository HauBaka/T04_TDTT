
from datetime import datetime, timezone
from core.exceptions import AppException, NotFoundError
from schemas.response_schema import ResponseSchema
from schemas.response_schema import ResponseSchema
from schemas.trip_schema import TripCreateRequest, TripMemberTracking, TripResponse, TripStatus, TripUpdateRequest
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
        
        if creator_info.get("current_trip"):
            raise AppException(status_code=400, message="You are already in an active trip.")
        
        # Tạo trip mới
        new_trip = await self.trip_repo.create(creator_uid, trip_data.model_dump())
        if not new_trip:
            raise AppException(status_code=500, message="Failed to create trip.")
        
        trip_id = new_trip.get("id")
        if not trip_id:
            raise AppException(status_code = 500, message = "Trip ID is missing after creation.")
        member_data = {
            creator_uid: {
                "display_name": creator_info.get("display_name", "Unknown"),
                "avatar_url": creator_info.get("avatar_url"),
                "role": "owner"
            }
        }
        updated_trip = await self.trip_repo.add_members(trip_id, member_data)
        
        await self.user_repo.update_user(creator_uid, {"current_trip": trip_id})
        
        return ResponseSchema(
            message="Trip created successfully",
            data=TripResponse(**(updated_trip or new_trip))
        )
    
    async def get_trip(self, trip_id: str, requester_uid: str | None) -> ResponseSchema[TripResponse]:
        """Lấy thông tin một trip theo ID."""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundError("Trip not found.")
        member_uids = trip.get("member_uids", [])
        if requester_uid and requester_uid not in member_uids:
            raise AppException(status_code=403, message="You are not a member of this trip.")
        
        return ResponseSchema(data=TripResponse(**trip))
    
    async def update_trip(self, trip_id: str, requester_uid: str, update_data: TripUpdateRequest) -> ResponseSchema[TripResponse]:
        """Cập nhật thông tin một trip."""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundError("Trip not found.")
            
        owner_uid = trip.get("owner_uid")
        if requester_uid != owner_uid:
            raise AppException(status_code=403, message="Only the trip owner can update this trip.")
            
        trip_status = trip.get("status", TripStatus.WAITING.value)
        if trip_status != TripStatus.WAITING.value:
            raise AppException(
                status_code=400, 
                message="Can only update trip details when status is WAITING."
            )
            
        update_payload = update_data.model_dump(exclude_unset=True)
        updated_trip = await self.trip_repo.update(trip_id, update_payload)
        
        if not updated_trip:
            raise AppException(status_code=500, message="Failed to update trip.")
        #xử lý endtrip
        new_status = update_payload.get("status")
        if new_status == TripStatus.ENDED.value or new_status == TripStatus.ENDED:
            member_uids = updated_trip.get("member_uids", [])
            if member_uids:
                await self.user_repo.batch_update_current_trip(member_uids, None)
                
        return ResponseSchema(data=TripResponse(**updated_trip))
    
    async def delete_trip(self, trip_id: str, requester_uid: str) -> ResponseSchema[bool]:
        """Xóa một trip."""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundError("Trip not found.")
        owner_uid = trip.get("owner_uid")
        if requester_uid != owner_uid:
            raise AppException(status_code=403, message="Only the trip owner can delete this trip.")
        success = await self.trip_repo.delete(trip_id)
        if not success:
            raise AppException(status_code=500, message="Failed to delete trip.")
        member_uids = trip.get("member_uids", [])
        if member_uids:
            await self.user_repo.batch_update_current_trip(member_uids, None)
            
        return ResponseSchema(message="Trip deleted successfully", data=success)
    
    async def add_members_to_trip(self, trip_id: str, requester_uid: str, member_uids: list[str]) -> ResponseSchema[TripResponse]:
        """Thêm nhiều thành viên vào một trip."""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundError("Trip not found.")
            
        trip_status = trip.get("status")
        if trip_status != TripStatus.WAITING.value:
            raise AppException(
                status_code=400, 
                message=f"Cannot add members. Trip is currently in '{trip_status}' status, expected 'waiting'."
            )
            
        current_members = trip.get("member_uids", [])
        if requester_uid not in current_members:
            raise AppException(status_code=403, message="You must be a member to add others.")
            
        new_member_uids = [uid for uid in member_uids if uid not in current_members]
        if not new_member_uids:
            raise AppException(status_code=400, message="All members are already in this trip.")
        users_info = await self.user_repo.get_users(new_member_uids)
        
        members_data_to_add = {}
        for uid in new_member_uids:
            user_info = users_info.get(uid)
            if not user_info:
                raise NotFoundError(f"User {uid} not found in system.")
            #kiểm tra đảm bảo các user chuẩn bị thêm chưa tham gia trip nào khác
            if user_info.get("current_trip"):
                display_name = user_info.get("display_name", uid)
                raise AppException(status_code=400, message=f"User {display_name} is already in another active trip.")   
            members_data_to_add[uid] = {
                "display_name": user_info.get("display_name", "Unknown"),
                "avatar_url": user_info.get("avatar_url"),
                "role": "member"
            }
        updated_trip = await self.trip_repo.add_members(trip_id, members_data_to_add)
        
        if not updated_trip:
            raise AppException(status_code=500, message="Failed to add members to trip.")
        #Update: current_trip = trip_id cho các new member
        await self.user_repo.batch_update_current_trip(new_member_uids, trip_id)
        
        return ResponseSchema(data=TripResponse(**updated_trip))
    
    async def remove_members_from_trip(self, trip_id: str, requester_uid: str, target_uids: list[str]) -> ResponseSchema[TripResponse]:
        """Xóa nhiều thành viên khỏi một trip."""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundError("Trip not found.")
        
        owner_uid = trip.get("owner_uid")
        current_members = trip.get("member_uids", [])
        
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
        await self.user_repo.batch_update_current_trip(target_uids, None)
        return ResponseSchema(data=TripResponse(**updated_trip))

    async def get_trip_members(self, trip_id: str, requester_uid: str) -> ResponseSchema[list[TripMemberTracking]]:
        """Lấy thông tin thành viên của một trip."""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundError("Trip not found.")
        current_members = trip.get("member_uids", [])
        if requester_uid not in current_members:
            raise AppException(
                status_code=403, 
                message="You must be a member of this trip to view its members."
            )
        members_data = await self.trip_repo.get_members(trip_id)
        members = [TripMemberTracking(**member) for member in members_data]
        
        return ResponseSchema(data=members)

trip_service = TripService()
