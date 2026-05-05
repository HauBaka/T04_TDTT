import asyncio
from datetime import datetime, timezone
from repositories.base_repo import BaseRepository
from schemas.trip_schema import TripStatus
class TripRepository(BaseRepository):
    def __init__(self):
        super().__init__("trips")

    async def create(self, uid: str, trip_data: dict) -> dict | None:
        """Tạo một trip mới."""
        now = datetime.now(timezone.utc)
        payload = trip_data.copy()
        
        payload.update({
            "owner_uid": uid,
            "created_at": now,
            "updated_at": now,
            "status": TripStatus.WAITING.value
        })

        trip_id = await self._create(payload)

        return await self._get_by_id(trip_id)
    
    async def get_by_id(self, trip_id: str) -> dict | None:
        """Lấy thông tin một trip theo ID."""
        trip_data = await self._get_by_id(trip_id)
        if not trip_data:
            return None
        
        members_detail = await self.get_members(trip_id)    
        trip_data["members"] = members_detail

        return trip_data
    
    async def update(self, trip_id: str, update_data: dict) -> dict | None:
        """Cập nhật thông tin một trip."""
        payload = {k: v for k, v in update_data.items() if v is not None}
        
        if not payload:
            return await self.get_by_id(trip_id)
        
        payload["updated_at"] = datetime.now(timezone.utc)
        if "status" in payload and hasattr(payload["status"],"value"):
            payload["status"] = payload["status"].value

        #sd hàm base
        await self._update(trip_id, payload)
        return await self.get_by_id(trip_id)
    
    async def add_members(self, trip_id: str, members_data: list[str]) -> dict | None:
        """Thêm member:
        BỎ: 1. Cập nhật UID vào mảng member_uids ở document_trip.
        2. Tạo document chứa thông tin chi tiết trong subcollection"""
        if not members_data:
            return await self.get_by_id(trip_id)

        db = self._get_db()
        batch = db.batch()
        now = datetime.now(timezone.utc)

        trip_ref = db.collection("trips").document(trip_id)
        batch.update(trip_ref, {
            "updated_at": now
        })

        for uid in members_data:
            member_ref = trip_ref.collection("members").document(uid)
            batch.set(member_ref, {"uid": uid, "joined_at": now})

        await batch.commit()
        return await self.get_by_id(trip_id)
        
    async def remove_members(self, trip_id: str, uids: list[str]) -> dict | None:
        """Xóa member:
        Bỏ: 1. Xóa uid khỏi mảng 'member_uids' ở document trip
        2. Xóa document của member đó khỏi subcollection"""
        if not uids:
            return await self.get_by_id(trip_id)

        db = self._get_db()
        batch = db.batch()
        trip_ref = db.collection("trips").document(trip_id)
        batch.update(trip_ref, {
            "updated_at": datetime.now(timezone.utc)
        })

        for uid in uids:
            member_ref = trip_ref.collection("members").document(uid)
            batch.delete(member_ref)
            
        await batch.commit()

        return await self.get_by_id(trip_id)       
        
    async def update_members(self, trip_id: str, updates_data: dict[str,dict]) -> list[dict]:
        """cập nhật thông tin của nhiều member trong collection"""
        if not trip_id or not updates_data:
            return []

        db = self._get_db()
        batch = db.batch()
        members_ref = db.collection("trips").document(trip_id).collection("members")
        valid_uids = []
        for uid, update_data in updates_data.items():
            payload = update_data.copy()
            
            if payload:
                batch.set(members_ref.document(uid), payload, merge=True) 
                valid_uids.append(uid)

        if not valid_uids:
            return []
        
        await batch.commit()
        
        tasks = [members_ref.document(uid).get() for uid in valid_uids]
        docs = await asyncio.gather(*tasks)
        
        updated_members = []

        for doc in docs:
            if doc.exists:
                member_data = doc.to_dict()
                member_data["uid"] = doc.id
                updated_members.append(member_data)

        return updated_members
    
    async def get_members(self, trip_id: str) -> list[dict]:
        "lấy danh sách member từ sub-collection"
        if not trip_id:
            return []
        db = self._get_db()
        docs = db.collection("trips").document(trip_id).collection("members").stream()
        
        members = []
        async for doc in docs:
            member_data = doc.to_dict()
            if member_data:
                member_data["uid"] = doc.id
                members.append(member_data)
        return members
    
    async def delete(self, trip_id: str) -> bool:
        """Xóa một trip."""
        if not trip_id:
            return False

        db = self._get_db()
        members_ref = db.collection("trips").document(trip_id).collection("members")
        
        docs = members_ref.stream()
        batch = db.batch()
        has_members = False
        
        async for doc in docs:
            batch.delete(doc.reference)
            has_members = True
            
        if has_members:
            await batch.commit()
        return await self._delete(trip_id)
    
trip_repo = TripRepository()
