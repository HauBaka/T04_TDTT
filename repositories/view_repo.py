from datetime import timedelta

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from loguru import logger

from core.cache import cache_get, cache_key, cache_set, cache_update_fields
from repositories.base_repo import BaseRepository
from schemas.collection_schema import CollectionDocument, CollectionVisibility
from schemas.discover_schema import HotelDocument
from schemas.view_schema import TopType, ViewLogDocument, ViewStats, ViewTargetType

MODEL_MAP = {
    ViewTargetType.COLLECTION: CollectionDocument,
    ViewTargetType.HOTEL: HotelDocument,
}


class ViewRepository(BaseRepository):
    def __init__(self):
        super().__init__("view_logs")

    async def add_view(
        self, viewer_id: str, target_id: str, target_type: ViewTargetType
    ):
        now = self._current_timestamp
        iso = now.isocalendar()
        cur_year = iso[0]
        cur_week = iso[1]

        doc_id = f"{viewer_id}_{target_type.value}_{target_id}"
        batch = self._db.batch()

        # Cập nhật log xem của người dùng
        log_ref = self._collection.document(doc_id)
        log_doc = await log_ref.get()

        if not log_doc.exists:
            log = ViewLogDocument(
                viewer_id=viewer_id,
                target_id=target_id,
                target_type=target_type,
                last_update=now,
            )
            batch.set(log_ref, log.model_dump(mode="python"))
        else:
            log_data = log_doc.to_dict() or {}
            log = ViewLogDocument.model_validate(log_data)

            if now - log.last_update < timedelta(minutes=30):
                return

            log.last_update = now

            batch.update(log_ref, {"last_update": log.last_update})
        # Xác định collection và document của target
        target_ref = self._db.collection(target_type.value).document(target_id)
        target_doc = await target_ref.get()

        if not target_doc.exists:
            return

        target_data = target_doc.to_dict() or {}
        views = ViewStats.model_validate(target_data.get("views", {}))

        update_data = {
            "views.total_views": firestore.Increment(1),
            "views.last_update": now,
        }

        if views.year == cur_year and views.week == cur_week:
            # Cùng tuần: Tăng total_views và weekly_views thêm 1
            update_data["views.weekly_views"] = firestore.Increment(1)
        else:
            # Sang tuần mới: Tăng total_views, nhưng reset weekly_views về 1 và cập nhật mốc thời gian
            update_data.update(
                {
                    "views.weekly_views": 1,
                    "views.year": cur_year,
                    "views.week": cur_week,
                }
            )

        batch.update(target_ref, update_data)

        await batch.commit()
        logger.debug(
            f"Added view for {target_type.value} {target_id} by user {viewer_id}"
        )
        logger.debug(cache_key(target_type.value.lower(), "id", doc_id))
        await cache_update_fields(
            cache_key(target_type.value.lower(), "id", target_id),
            update_data,
        )

    async def get_top_views(
        self,
        target_type: ViewTargetType,
        limit: int = 10,
        page: int = 1,
        top_type: TopType = TopType.ALL_TIME,
    ) -> list[CollectionDocument | HotelDocument]:
        db = self._db

        now = self._current_timestamp
        iso = now.isocalendar()
        cur_year = iso[0]
        cur_week = iso[1]
        model_class = MODEL_MAP.get(target_type)
        if not model_class:
            return []

        cache_id = cache_key(
            "top_views",
            target_type.value,
            top_type.value,
            str(page),
            str(limit),
        )
        cached = await cache_get(cache_id)

        if cached is not None:
            return [model_class.model_validate(item) for item in cached]

        query = db.collection(target_type.value)
        if target_type == ViewTargetType.COLLECTION:
            query = query.where(
                filter=FieldFilter(
                    "visibility", "==", CollectionVisibility.PUBLIC.value
                )
            )

        if top_type == TopType.ALL_TIME:
            # Lấy top views theo tổng số lần xem
            query = query.order_by(
                "views.total_views", direction=firestore.Query.DESCENDING
            )
        else:
            # Lấy top views theo tuần
            query = (
                query.where(filter=FieldFilter("views.year", "==", cur_year))
                .where(filter=FieldFilter("views.week", "==", cur_week))
                .order_by("views.weekly_views", direction=firestore.Query.DESCENDING)
            )

        offset = (page - 1) * limit
        docs = await query.offset(offset).limit(limit).get()

        results = []

        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id

            model_class = MODEL_MAP.get(target_type)
            if model_class:
                results.append(model_class.model_validate(data))

        await cache_set(
            cache_id,
            [item.model_dump(mode="json") for item in results],
            ttl_seconds=300,
        )

        return results


view_repository = ViewRepository()
