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
        "status": TripStatus.WAITING,
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
        payload["update_at"] = datetime.now(timezone.utc)
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

    async def delete(self, trip_id: str) -> bool:
        """Xóa một trip."""
        return await self._delete(trip_id)
    
trip_repo = TripRepository()