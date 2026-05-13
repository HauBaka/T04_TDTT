from __future__ import annotations
import logging
from datetime import datetime

from google.cloud.firestore_v1 import FieldFilter, Query
from repositories.base_repo import BaseRepository
from core.exceptions import NotFoundError, AppException
from schemas.user_behavior_schema import UserBehaviorEventDocument

logger = logging.getLogger(__name__)

_FIRESTORE_BATCH_LIMIT = 500
class BehaviorEventRepo(BaseRepository):

    """Interface tối thiểu cho persistence layer của behavior events."""
    def __init__(self):
        super().__init__("user_behavior_events")
    async def create_event(self, event: UserBehaviorEventDocument) -> str:
        """Lưu một event vào Firestore, trả về document ID."""
        event_data = event.model_dump(exclude={"id"})
        return await self._create(event_data,doc_id = event.id or None)
    

    async def list_events_for_user(
        self, user_uid: str, limit: int = 100, last_doc = None
    ) -> list[UserBehaviorEventDocument]:
        """Lấy danh sách events của user, sắp xếp theo created_at DESC."""
        query = (
            self._collection.where(filter=FieldFilter("user_uid", "==", user_uid))
            .order_by("created_at", direction=Query.DESCENDING)
            .limit(limit)
        )
        if last_doc:
            query = query.start_after(last_doc)
            
        docs = await query.get()
        events: list[UserBehaviorEventDocument] = []

        for doc in docs:
            data = doc.to_dict()
            if data:
                data["id"] = doc.id
                events.append(UserBehaviorEventDocument.model_validate(data))
            try:
                events.append(UserBehaviorEventDocument.model_validate(data))
            except Exception as e:
                logger.error(f"Lỗi validate event {doc.id}: {e}")
        return events

    async def get_event_by_id(self, event_id: str) -> UserBehaviorEventDocument | None:
        """Lấy một event cụ thể theo ID."""
        data = await self._get_by_id(event_id)
        if not data:
            raise NotFoundError(f"Event id {event_id} không tồn tại")
        try:
            return UserBehaviorEventDocument.model_validate(data)
        except Exception as e:
            logger.error(f"Lỗi validate event {event_id}: {e}")
            raise AppException(status_code=500, message="Lỗi cấu trúc dữ liệu từ database")

    async def delete_events(self, event_ids: list[str]) -> int:
        """Xóa nhiều event theo danh sách ID."""
        if not event_ids:
            raise AppException(status_code=400, message="Danh sách event_ids không được rỗng")

        deleted_count = 0

        for i in range(0, len(event_ids), _FIRESTORE_BATCH_LIMIT):
            chunk = event_ids[i : i + _FIRESTORE_BATCH_LIMIT]
            batch = self._db.batch()

            for eid in chunk:
                batch.delete(self._collection.document(eid))

            await batch.commit()
            deleted_count += len(chunk)

        return deleted_count

    async def count_events_for_user(self, user_uid: str) -> int:
        """Đếm tổng số events của user."""
        agg_query = (
            self._collection
            .where(filter=FieldFilter("user_uid", "==", user_uid))
            .count(alias="total_events")
        )
        snapshot = await agg_query.get()

        try:
            return snapshot[0][0].value
        except (IndexError, AttributeError):
            logger.warning("Unexpected aggregation response for user_uid=%s", user_uid)
            return 0

    async def purge_older_than(self, cutoff_iso: str) -> int:
        """Xóa tất cả events có created_at < cutoff_iso."""
        try:
            cutoff_dt = datetime.fromisoformat(cutoff_iso.replace("Z", "+00:00"))
        except ValueError as e:
            logger.error(f"Invalid cutoff_iso format: {cutoff_iso}. Error: {e}")
            return 0
        query = self._collection.where(filter=FieldFilter("created_at", "<", cutoff_dt))

        deleted_count = 0
        batch = self._db.batch()
        batch_ops = 0

        async for doc in query.stream():
            batch.delete(doc.reference)
            batch_ops += 1
            deleted_count += 1

            if batch_ops == _FIRESTORE_BATCH_LIMIT:
                await batch.commit()
                batch = self._db.batch()
                batch_ops = 0

        if batch_ops > 0:
            await batch.commit()

        return deleted_count
    
behavior_event_repo = BehaviorEventRepo()