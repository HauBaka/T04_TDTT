from __future__ import annotations


import uuid
from datetime import datetime, timedelta, timezone
from repositories.behavior_event_repo import behavior_event_repo
from schemas.user_behavior_schema import UserBehaviorEvent, UserEventType


class BehaviorService:
    """Service quản lý behavior tracking của người dùng."""

    def __init__(self):
        """Khởi tạo service với repository implementation."""
        self.repo = behavior_event_repo
        
    async def record_event(
        self,
        user_id: str,
        event_type: UserEventType,
        target_id: str | None = None,
        target_name: str | None = None,
        metadata: dict[str, str] | None = None,
        source: str | None = None,
    ) -> str:
        """Ghi nhận một sự kiện hành vi của người dùng."""
        event_id = uuid.uuid4().hex
        meta = metadata.copy() if metadata else {}
        if source:
            meta["source"] = source
        event = UserBehaviorEvent(
            id=event_id,
            user_id=user_id,
            event_type=event_type,
            target_id=target_id,
            target_name=target_name,
            metadata=meta
        )
        return await self.repo.create_event(event)

    async def get_recent_events(
        self,
        user_id: str,
        limit: int = 100,
        last_doc=None,
    ) -> list[UserBehaviorEvent]:
        """Lấy các events gần đây nhất của user."""
        return await self.repo.list_events_for_user(user_id, limit=limit, last_doc=last_doc)

    async def get_event_count(self, user_id: str) -> int:
        """Đếm tổng số events của user."""
        return await self.repo.count_events_for_user(user_id)

    async def delete_event(self, event_id: str) -> bool:
        """Xóa một event cụ thể (GDPR right to be forgotten)."""
        deleted_count = await self.repo.delete_events([event_id])
        return deleted_count > 0

    async def purge_old_events(self, days: int = 365) -> int:
        """Xóa events cũ hơn N ngày (retention policy)."""
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff_dt.isoformat().replace("+00:00", "Z")
        return await self.repo.purge_older_than(cutoff_iso)
    
behavior_service = BehaviorService()
