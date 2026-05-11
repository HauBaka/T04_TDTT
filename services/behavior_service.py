from __future__ import annotations

from typing import Iterable

from repositories.behavior_event_repo import behavior_event_repo
from schemas.user_preference_schema import UserBehaviorEvent, UserEventType


class BehaviorService:
    """Service quản lý behavior tracking của người dùng."""

    def __init__(self):
        """Khởi tạo service với repository implementation."""
        self.repo = behavior_event_repo
        
    def record_event(
        self,
        user_id: str,
        event_type: UserEventType,
        target_id: str | None = None,
        target_name: str | None = None,
        metadata: dict[str, str] | None = None,
        source: str | None = None,
    ) -> str:
        """TODO: Ghi nhận một sự kiện hành vi của người dùng."""
        raise NotImplementedError()

    def get_recent_events(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> Iterable[UserBehaviorEvent]:
        """TODO: Lấy các events gần đây nhất của user."""
        raise NotImplementedError()

    def get_event_count(self, user_id: str) -> int:
        """TODO: Đếm tổng số events của user."""
        raise NotImplementedError()

    def delete_event(self, event_id: str) -> bool:
        """TODO: Xóa một event cụ thể (GDPR right to be forgotten)."""
        raise NotImplementedError()

    def purge_old_events(self, days: int = 365) -> int:
        """TODO: Xóa events cũ hơn N ngày (retention policy)."""
        raise NotImplementedError()
    
behavior_service = BehaviorService()
