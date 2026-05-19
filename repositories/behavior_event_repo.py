from __future__ import annotations

import logging
from datetime import datetime

from google.cloud.firestore_v1 import FieldFilter, Query
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import BadRequestError, InternalServerError, NotFoundError
from repositories.base_repo import BaseRepository
from schemas.user_behavior_schema import (
    GetRecentBehaviourEventRequest,
    UserBehaviorEventCreateRequest,
    UserBehaviorEventDocument,
)

logger = logging.getLogger(__name__)

_FIRESTORE_BATCH_LIMIT = 500


class BehaviorEventRepo(BaseRepository):
    """Interface tối thiểu cho persistence layer của behavior events."""

    def __init__(self):
        super().__init__("users")
        self._subcol_name = "behavior_events"

    def _user_events_ref(self, user_uid: str):
        """Hàm phụ trợ lấy reference đến thư mục behavior_events của 1 user cụ thể"""
        return self._collection.document(user_uid).collection(self._subcol_name)

    async def create_event(
        self, user_uid: str, request: UserBehaviorEventCreateRequest
    ) -> str:
        """Lưu một event vào Firestore, trả về document ID."""

        meta = request.metadata.copy() if request.metadata else {}

        if request.source:
            meta["source"] = request.source

        ref = self._user_events_ref(user_uid).document()

        event_doc = UserBehaviorEventDocument(
            id=ref.id,
            user_uid=user_uid,
            event_type=request.event_type,
            target_id=request.target_id,
            target_name=request.target_name,
            created_at=self._current_timestamp,
            metadata=meta,
        )

        event_data = event_doc.model_dump(exclude_none=False)
        await ref.set(event_data)
        return ref.id

    async def list_events_for_user(
        self, request: GetRecentBehaviourEventRequest
    ) -> list[UserBehaviorEventDocument]:
        """Lấy danh sách events của user, sắp xếp theo created_at DESC."""
        query = (
            self._user_events_ref(request.user_uid)
            .order_by("created_at", direction=Query.DESCENDING)
            .limit(request.limit)
        )
        if request.last_doc:
            query = query.start_after(request.last_doc)

        docs = await query.get()
        events: list[UserBehaviorEventDocument] = []

        for doc in docs:
            data = doc.to_dict()
            if data:
                data["id"] = doc.id
            try:
                events.append(UserBehaviorEventDocument.model_validate(data))
            except PydanticValidationError as e:
                logger.error(f"Validation error for event {doc.id}: {e}")
                continue
        return events

    async def get_event_by_id(
        self, user_uid: str, event_id: str
    ) -> UserBehaviorEventDocument:
        """Lấy một event cụ thể theo ID."""
        doc = await self._user_events_ref(user_uid).document(event_id).get()
        data = doc.to_dict() if doc.exists else None

        if not data:
            raise NotFoundError(message=f"Event ID {event_id} not found")

        try:
            data["id"] = doc.id
            return UserBehaviorEventDocument.model_validate(data)
        except PydanticValidationError as e:
            logger.error(f"Validation error for event {event_id}: {e}")
            raise InternalServerError(message="Invalid data structure from database")

    async def delete_events(self, user_uid: str, event_ids: list[str]) -> int:
        """Xóa nhiều event theo danh sách ID."""
        if not event_ids:
            raise BadRequestError(message="Event IDs list cannot be empty")

        deleted_count = 0
        sub_ref = self._user_events_ref(user_uid)

        for i in range(0, len(event_ids), _FIRESTORE_BATCH_LIMIT):
            chunk = event_ids[i : i + _FIRESTORE_BATCH_LIMIT]
            batch = self._db.batch()

            for eid in chunk:
                batch.delete(sub_ref.document(eid))

            await batch.commit()
            deleted_count += len(chunk)

        return deleted_count

    async def count_events_for_user(self, user_uid: str) -> int:
        """Đếm tổng số events của user."""
        agg_query = self._user_events_ref(user_uid).count(alias="total_events")
        snapshot = await agg_query.get()

        try:
            return snapshot[0][0].value
        except (IndexError, AttributeError):
            logger.warning(f"Unexpected aggregation response for user_uid={user_uid}")
            return 0

    async def purge_older_than(self, user_uid: str, cutoff_dt: datetime) -> int:
        """Xóa tất cả events có created_at < cutoff_dt."""

        query = self._user_events_ref(user_uid).where(
            filter=FieldFilter("created_at", "<", cutoff_dt)
        )
        docs = await query.get()

        deleted_count = 0
        batch = self._db.batch()
        batch_ops = 0

        for doc in docs:
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
