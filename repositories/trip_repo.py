from datetime import datetime, timezone
from google.cloud import firestore as fs

from repositories.base_repo import BaseRepository
from schemas.trip_schema import TripStatus
class TripRepository(BaseRepository):
    def __init__(self):
        super().__init__("trips")

    async def create(self,uid: str, trip_data: dict) -> dict | None:
        """Tạo một trip mới."""
        now = datetime.now(timezone.utc)
        payload = trip_data.copy()
        
        payload.update({
        "owner_uid": uid,
        "created_at": now,
        "updated_at": now,
        "status": TripStatus.WAITING.value,
        "member_uids": [uid]
    })
        trip_id = await self._create(payload)
        return await self._get_by_id(trip_id)
        
    
    async def get_by_id(self, trip_id: str) -> dict | None:
        """Lấy thông tin một trip theo ID."""
        return await self._get_by_id(trip_id)
    
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
    
    async def add_members(self, trip_id: str, member_uids: list[str]) -> dict | None:
        """Thêm thành viên vào một trip."""
        payload = {
            "member_uids": fs.ArrayUnion(member_uids),
            "updated_at": datetime.now(timezone.utc)
        }
        await self._update(trip_id, payload)
        return await self._get_by_id(trip_id)
    
    async def remove_members(self, trip_id: str, member_uids: list[str]) -> dict | None:
        """Xóa thành viên khỏi một trip."""
        payload = {
            "member_uids": fs.ArrayRemove(member_uids),
            "updated_at": datetime.now(timezone.utc)
        }
        await self._update(trip_id, payload)
        return await self._get_by_id(trip_id)
    async def add_member_to_subcollection(self,trip_id: str,uid: str,member_info: dict) -> dict | None:
        "add member vào sub_collection"
        db = self._get_db()
        member_data = member_info.copy()
        member_data.update({"uid": uid,"joined_at": datetime.now(timezone.utc)})
        ref = db.collection("trips").document(trip_id).collection("members").document(uid)
        await ref.set(member_data)
        return member_data 
    async def remove_member_from_subcollection(self, trip_id: str, uid: str) -> dict | None:
        "Xóa member khỏi collection"
        db = self._get_db()
        ref = db.collection("trips").document(trip_id).collection("members").document(uid)
        doc = await ref.get()
        if not doc.exist:
            return None
        deleted_data = doc.to_dict()
        deleted_data["uid"] = doc.id
        await ref.delete()
        return deleted_data
    async def get_members(self, trip_id: str) -> list[dict]:
        "lấy danh sách member từ collection"
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
    async def update_member_in_subcollection(self,trip_id: str,uid: str,update_data: dict) -> dict | None:
        "update member infor trong subcollection và return về thông tin mới nhất"
        db = self._get_db()
        payload = {k: v for k, v in update_data.items() if v is not None}
        
        ref = db.collection("trips").document(trip_id).collection("members").document(uid)
        if payload:
            await ref.update(payload)
        doc = await ref.get()
        if not doc.exists:
            return None
        member_data = doc.to_dict()
        member_data["uid"] = doc.id
        return member_data
    async def delete(self, trip_id: str) -> bool:
        """Xóa một trip."""
        return await self._delete(trip_id)
    
trip_repo = TripRepository()
