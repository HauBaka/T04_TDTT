from __future__ import annotations

from datetime import datetime, timedelta, timezone
from repositories.behavior_event_repo import behavior_event_repo
from schemas.user_behavior_schema import (
    UserBehaviorEventCreateRequest,
    GetRecentBehaviourEventRequest,
    UserBehaviorEventDocument
)


class BehaviorService:
    """Service quản lý behavior tracking của người dùng."""

    def __init__(self):
        """Khởi tạo service với repository implementation."""
        self.repo = behavior_event_repo
        
    async def record_event(self,user_uid: str, request: UserBehaviorEventCreateRequest) -> str:
        """Ghi nhận một sự kiện hành vi của người dùng."""
        return await self.repo.create_event(user_uid, request)
        

    async def get_recent_events(
        self,
        request: GetRecentBehaviourEventRequest
    ) -> list[UserBehaviorEventDocument]:
        """Lấy các events gần đây nhất của user."""
        return await self.repo.list_events_for_user(request)
    async def get_event_count(self, user_uid: str) -> int:
        """Đếm tổng số events của user."""
        return await self.repo.count_events_for_user(user_uid=user_uid)

    async def delete_event(self,user_uid: str, event_id: str) -> bool:
        """Xóa một event cụ thể (GDPR right to be forgotten)."""
        deleted_count = await self.repo.delete_events(user_uid, [event_id])
        return deleted_count > 0

    async def purge_old_events(self, days: int = 365) -> int:
        """Xóa events cũ hơn N ngày (retention policy)."""
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff_dt.isoformat().replace("+00:00", "Z")
        return await self.repo.purge_older_than(cutoff_iso)
    
behavior_service = BehaviorService()
