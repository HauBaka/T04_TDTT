from __future__ import annotations

from typing import Iterable

from repositories.base_repo import BaseRepository

from schemas.user_behavior_schema import UserBehaviorEvent


class BehaviorEventRepo(BaseRepository):

    """Interface tối thiểu cho persistence layer của behavior events."""

    def create_event(self, event: UserBehaviorEvent) -> str:
        """Persist một event và trả về ID của nó."""
        raise NotImplementedError

    def list_events_for_user(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> Iterable[UserBehaviorEvent]:
        """Lấy danh sách events của user, sắp xếp theo created_at DESC."""
        raise NotImplementedError

    def get_event_by_id(self, event_id: str) -> UserBehaviorEvent | None:
        """Lấy một event cụ thể theo ID."""
        raise NotImplementedError

    def delete_events(self, event_ids: list[str]) -> int:
            """Xóa nhiều event theo danh sách ID."""
            raise NotImplementedError

    def count_events_for_user(self, user_id: str) -> int:
        """Đếm tổng số events của user."""
        raise NotImplementedError

    def purge_older_than(self, cutoff_iso: str) -> int:
        """Xóa tất cả events có created_at < cutoff_iso."""
        raise NotImplementedError
    
behavior_event_repo= BehaviorEventRepo()