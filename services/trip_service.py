
from loguru import logger

from core.exceptions import AppException, BadRequestError, NotFoundError, PermissionDeniedError
from repositories.hotel_repo import hotel_repo
from schemas.response_schema import ResponseSchema
from schemas.trip_schema import TripMemberResponse, TripCreateRequest, TripDocument, TripPlaceResponse, TripResponse, TripStatus, TripUpdateRequest
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
        # Kiểm tra nếu creator đang tham gia trip khác
        if creator_info.current_trip:
            raise AppException(status_code=400, message="You are already in a trip.")
        
        # Kiểm tra place_id hợp lệ
        if not await hotel_repo.valid_ids([trip_data.place_id]):
            raise BadRequestError(message="Invalid place_id.")
        
        # Tạo trip mới
        trip = await self.trip_repo.create(creator_uid, trip_data)
        
        return await self._build_trip_response(trip)
    
    async def get_trip(self, trip_id: str, requester_uid: str | None) -> ResponseSchema[TripResponse]:
        """Lấy thông tin một trip theo ID."""
        trip = await self.trip_repo.get_by_id(trip_id)

        if requester_uid and requester_uid not in trip.member_uids:
            raise PermissionDeniedError(message="You are not a member of this trip.")

        return await self._build_trip_response(trip)
    
    async def update_trip(self, trip_id: str, requester_uid: str, update_data: TripUpdateRequest) -> ResponseSchema[TripResponse]:
        trip = await self.trip_repo.get_by_id(trip_id)

        # Chỉ owner mới được phép update trip
        if requester_uid != trip.owner_uid:
            raise PermissionDeniedError(message="Only the trip owner can update this trip.")

        update_payload = update_data.model_dump(exclude_unset=True)
        new_status = update_payload.get("status")

        metadata_fields = {"name", "place_id", "start_at", "end_at"} # Metadata chỉ được sửa khi WAITING
        if update_payload.keys() & metadata_fields:
            if trip.status != TripStatus.WAITING:
                raise BadRequestError(
                    message="Can only update trip details when status is WAITING."
                )

        # Kiểm tra place_id hợp lệ nếu có thay đổi
        if "place_id" in update_payload and not await hotel_repo.valid_ids([update_payload["place_id"]]):
            raise BadRequestError(message="Invalid place_id.")

        # Update trip
        updated_trip = await self.trip_repo.update(trip_id, update_data)

        # Nếu status được cập nhật thành ENDED, tự động set current_trip = None cho tất cả member
        if new_status in (TripStatus.ENDED.value, TripStatus.ENDED):
            member_uids = trip.member_uids

            if member_uids:
                await self.user_repo.batch_update_users(member_uids, [{"current_trip": None} for _ in member_uids])

        return  await self._build_trip_response(updated_trip)

    async def delete_trip(self, trip_id: str, requester_uid: str) -> ResponseSchema[bool]:
        """Xóa một trip."""
        trip = await self.trip_repo.get_by_id(trip_id)
        
        # Check quyền
        if requester_uid != trip.owner_uid:
            raise PermissionDeniedError(message="Only the trip owner can delete this trip.")
        
        # Trước khi xóa, set current_trip = None cho tất cả member đang tham gia
        await self.user_repo.batch_update_users(trip.member_uids, [{"current_trip": None} for _ in trip.member_uids])

        await self.trip_repo.delete(trip_id)
        return ResponseSchema(data=True)
    
    async def add_members_to_trip(self, trip_id: str, requester_uid: str, member_uids: list[str]) -> ResponseSchema[TripResponse]:
        """Thêm nhiều thành viên vào một trip."""
        trip = await self.trip_repo.get_by_id(trip_id)
        # Chỉ được phép thêm khi trip đang ở trạng thái WAITING
        if trip.status != TripStatus.WAITING:
            raise BadRequestError(
                message=f"Cannot add members. Trip is currently in '{trip.status.value}' status, expected 'waiting'."
            )
        
        # Chỉ member mới được thêm thành viên khác vào trip
        if requester_uid not in trip.member_uids:
            raise PermissionDeniedError(message="You must be a member to add others.")
        
        # Loại bỏ những UID đã là member để tránh lỗi khi thêm trùng
        new_member_uids = [uid for uid in member_uids if uid not in trip.member_uids]
        if not new_member_uids:
            raise PermissionDeniedError(message="All members are already in this trip.")
        
        # Kiểm tra thông tin của các UID mới trước khi thêm
        users_info = await self.user_repo.get_users(new_member_uids)
        
        members_to_add = []
        for uid in new_member_uids:
            user_info = users_info.get(uid)
            if not user_info:
                raise NotFoundError(f"User {uid} not found in system.")
            
            # kiểm tra đảm bảo các user chuẩn bị thêm chưa tham gia trip nào khác
            if user_info.current_trip:
                raise BadRequestError(message=f"User {user_info.display_name} is already in a trip.")   
            
            members_to_add.append(uid)

        updated_trip = await self.trip_repo.add_members(trip_id, members_to_add)
        
        return await self._build_trip_response(updated_trip)
    
    async def remove_members_from_trip(self, trip_id: str, requester_uid: str, target_uids: list[str]) -> ResponseSchema[TripResponse]:
        """Xóa nhiều thành viên khỏi một trip."""
        trip = await self.trip_repo.get_by_id(trip_id)
        
        # Kiểm tra quyền xóa
        is_owner = requester_uid == trip.owner_uid
        
        if not is_owner:
            # Member thường chỉ có thể xóa chính mình
            if len(target_uids) != 1 or target_uids[0] != requester_uid:
                raise PermissionDeniedError(
                    message="You do not have permission to remove other members."
                )

        # Kiểm tra không xóa owner
        if trip.owner_uid in target_uids:
            raise BadRequestError(message="Cannot remove the trip owner.")
        
        # Kiểm tra tất cả target đều là member
        for uid in target_uids:
            if uid not in trip.member_uids:
                raise BadRequestError(message=f"User {uid} is not a member of this trip.")
        
        # Xóa member data từ subcollection
        updated_trip = await self.trip_repo.remove_members(trip_id, target_uids)
        
        return await self._build_trip_response(updated_trip)

    async def get_trip_members(self, trip_id: str, requester_uid: str) -> ResponseSchema[list[TripMemberResponse]]:
        """Lấy thông tin thành viên của một trip."""
        trip = await self.trip_repo.get_by_id(trip_id)
        
        # Chỉ member mới được xem danh sách thành viên
        trip_members_info = await self.trip_repo.get_members(trip_id)
        member_uids = [m.uid for m in trip_members_info]
        if requester_uid not in member_uids:
            raise PermissionDeniedError(message="You do not have permission to view members of this trip.")
        
        members_detail = await self.user_repo.get_users([m.uid for m in trip_members_info])

        members_response = []
        for member in trip_members_info:
            user_info = members_detail.get(member.uid)
            if not user_info:
                logger.warning(f"User info not found for member UID {member.uid} in trip {trip_id}")
                continue
            
            members_response.append(TripMemberResponse(
                uid=member.uid,
                username=user_info.username,
                display_name=user_info.display_name,
                avatar_url=user_info.avatar_url,
                tracking=member.tracking,
                joined_at=member.joined_at
            ))


        return ResponseSchema(data=members_response)

    async def _build_trip_response(self, trip_data: TripDocument) -> ResponseSchema[TripResponse]:
        """Hàm tiện ích để xây dựng TripResponse với thông tin member chi tiết."""
        place_doc = await hotel_repo.get_hotels([trip_data.place_id])
        hotel = place_doc.get(trip_data.place_id)
        place_response = TripPlaceResponse(**hotel.model_dump()) if hotel else None

        return ResponseSchema(data=TripResponse(
            id=trip_data.id,
            owner_uid=trip_data.owner_uid,
            name=trip_data.name,
            place=place_response,

            start_at=trip_data.start_at,
            end_at=trip_data.end_at,

            status=trip_data.status,
            member_count=len(trip_data.member_uids),

            created_at=trip_data.created_at,
            updated_at=trip_data.updated_at
        ))
    
trip_service = TripService()
