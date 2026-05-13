import asyncio
from loguru import logger
from pydantic import ValidationError as PydanticValidationError
from google.cloud import firestore
from core.exceptions import InternalServerError, ValidationError
from repositories.base_repo import BaseRepository
from schemas.trip_schema import TripCreateRequest, TripDocument, TripMemberDocument, TripStatus, TripUpdateRequest
class TripRepository(BaseRepository):
    def __init__(self):
        super().__init__("trips")

    async def create(self, uid: str, trip_data: TripCreateRequest) -> TripDocument:
        """Tạo một trip mới."""
        now = self._current_timestamp
        trip_doc = TripDocument(
            id = self._collection.document().id,
            owner_uid = uid,
            name = trip_data.name,
            place_id = trip_data.place_id,

            start_at = trip_data.start_at,
            end_at = trip_data.end_at,

            status = TripStatus.WAITING,
            member_uids = [uid],

            created_at = now,
            updated_at = now
        )

        await self._create(trip_doc.model_dump(mode="python", exclude_none=False), trip_doc.id)
        await self.add_members(trip_doc.id, [uid])  # Tự động thêm creator vào member list
        return trip_doc
    
    async def get_by_id(self, trip_id: str) -> TripDocument:
        """Lấy thông tin một trip theo ID."""
        trip_data = await self._get_by_id(trip_id)
        try:
            trip_doc = TripDocument.model_validate(trip_data)
        except PydanticValidationError as e:
            logger.error(f"Data validation error for trip_id {trip_id}: {e}")
            raise ValidationError("Data validation error")

        return trip_doc

    async def update(self, trip_id: str, update_data: TripUpdateRequest) -> TripDocument:
        """Cập nhật thông tin một trip."""
        payload = update_data.model_dump(mode="python", exclude_none=True)
        
        if not payload:
            raise ValidationError("No valid fields to update")
        
        payload["updated_at"] = self._current_timestamp
        if "status" in payload and hasattr(payload["status"],"value"):
            payload["status"] = payload["status"].value

        await self._update(trip_id, payload)
        return await self.get_by_id(trip_id)
    
    async def add_members(self, trip_id: str, members_data: list[str]) -> TripDocument:
        """Thêm member:
        1. Cập nhật UID vào mảng member_uids ở document_trip.
        2. Tạo document chứa thông tin chi tiết trong subcollection
        3. Update current_trip của users đó trong collection users
        """
        if not members_data:
            raise ValidationError("Member UIDs list cannot be empty")

        db = self._db
        batch = db.batch()
        now = self._current_timestamp
        # update trip document
        trip_ref = db.collection("trips").document(trip_id)
        batch.update(trip_ref, {
            "updated_at": now,
            "member_uids": firestore.ArrayUnion(members_data)
        })

        # update members subcollection
        for uid in members_data:
            member_ref = trip_ref.collection("members").document(uid)
            member = TripMemberDocument(uid=uid, tracking=None, joined_at=now)
            batch.set(member_ref, member.model_dump(mode="python"))

        # update current_trip của users đó trong collection users
        for uid in members_data:
            user_ref = db.collection("users").document(uid)
            batch.update(user_ref, {"current_trip": trip_id})

        await self._commit_batch(batch)
        return await self.get_by_id(trip_id)
        
    async def remove_members(self, trip_id: str, uids: list[str]) -> TripDocument:
        """Xóa member:
        1. Xóa uid khỏi mảng 'member_uids' ở document trip
        2. Xóa document của member đó khỏi subcollection
        3. Update current_trip của users đó trong collection users về None
        """
        if not uids:
            raise ValidationError("UID list cannot be empty")

        db = self._db
        batch = db.batch()
        # update trip document: xóa uid khỏi mảng member_uids
        trip_ref = db.collection("trips").document(trip_id)
        batch.update(trip_ref, {
            "updated_at": self._current_timestamp,
            "member_uids": firestore.ArrayRemove(uids)
        })
        # xóa document của member đó khỏi subcollection
        for uid in uids:
            member_ref = trip_ref.collection("members").document(uid)
            batch.delete(member_ref)
            
        # Update current_trip của users đó trong collection users về None
        for uid in uids:
            user_ref = db.collection("users").document(uid)
            batch.update(user_ref, {"current_trip": None})

        await self._commit_batch(batch)

        return await self.get_by_id(trip_id)
        
    async def update_members(self, trip_id: str, updates_data: dict[str, dict]) -> list[TripMemberDocument]:
        """cập nhật thông tin của nhiều member trong collection"""
        if not trip_id or not updates_data:
            raise ValidationError("Trip ID and updates data are required")

        db = self._db
        batch = db.batch()
        members_ref = db.collection("trips").document(trip_id).collection("members")
        valid_uids = []
        for uid, update_data in updates_data.items():
            payload = update_data.copy()
            
            if payload:
                batch.set(members_ref.document(uid), payload, merge=True) 
                valid_uids.append(uid)

        if not valid_uids:
            raise ValidationError("No valid member updates provided")
        
        await self._commit_batch(batch)
        
        tasks = [members_ref.document(uid).get() for uid in valid_uids]
        docs = await asyncio.gather(*tasks)
        updated_members: list[TripMemberDocument] = []

        for doc in docs:
            if doc.exists:
                member_data = doc.to_dict() or {}
                member_data["uid"] = doc.id
                try:
                    updated_members.append(TripMemberDocument.model_validate(member_data))
                except PydanticValidationError:
                    continue

        return updated_members
    
    async def get_members(self, trip_id: str) -> list[TripMemberDocument]:
        "lấy danh sách member từ sub-collection"
        if not trip_id:
            raise ValidationError("Trip ID is required")
        
        db = self._db
        docs = db.collection("trips").document(trip_id).collection("members").stream()
        
        members: list[TripMemberDocument] = []
        async for doc in docs:
            member_data = doc.to_dict() or {}
            member_data["uid"] = doc.id
            try:
                members.append(TripMemberDocument.model_validate(member_data))
            except PydanticValidationError:
                continue
        return members
    
    async def delete(self, trip_id: str) -> bool:
        """Xóa một trip."""
        if not trip_id:
            raise ValidationError("Trip ID is required")

        trip_ref = self._collection.document(trip_id)
        await self._delete_subcollection(trip_ref.collection("members"))
        return await self._delete(trip_id)
    
trip_repo = TripRepository()
