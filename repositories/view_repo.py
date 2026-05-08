from datetime import datetime, timedelta, timezone
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from repositories.base_repo import BaseRepository

from schemas.view_schema import TopType, ViewTargetType
from schemas.collection_schema import CollectionPublic, CollectionVisibility
from schemas.discover_schema import DiscoverHotel

MODEL_MAP = {
    ViewTargetType.COLLECTION: CollectionPublic,
    ViewTargetType.HOTEL: DiscoverHotel
}

class ViewRepository(BaseRepository):
    def __init__(self):
        super().__init__('view_logs')

    async def add_view(self, viewer_id: str, target_id: str, target_type: ViewTargetType):
        now = datetime.now(timezone.utc)
        iso = now.isocalendar()
        cur_year = iso[0]
        cur_week = iso[1]

        doc_id = f"{viewer_id}_{target_type.value}_{target_id}"
        db = self._get_db()
        batch = db.batch()

        # Cập nhật log xem của người dùng
        log_ref = db.collection('view_logs').document(doc_id)
        log_doc = await log_ref.get()


        if not log_doc.exists:
            batch.set(log_ref, {
                "viewer_id": viewer_id,
                "target_id": target_id,
                "target_type": target_type.value,
                "last_update": now
            })
        else:
            log_data = log_doc.to_dict() or {}
            last_update = log_data.get("last_update")
            if last_update and now - last_update < timedelta(minutes=30):
                return
            
            batch.update(log_ref, {
                "last_update": now
            })
        # Xác định collection và document của target
        target_collection_name = target_type.value
        target_ref = db.collection(target_collection_name).document(target_id)
        target_doc = await target_ref.get()

        if target_doc.exists:
            target_data = target_doc.to_dict() or {}
            views_data = target_data.get("views", {})
            
            old_year = views_data.get("year")
            old_week = views_data.get("week")

            if old_year == cur_year and old_week == cur_week:
                # Cùng tuần: Tăng total_views và weekly_views thêm 1
                batch.update(target_ref, {
                    "views.total_views": firestore.Increment(1),
                    "views.weekly_views": firestore.Increment(1),
                    "views.last_update": now
                })
            else:
                # Sang tuần mới: Tăng total_views, nhưng reset weekly_views về 1 và cập nhật mốc thời gian
                batch.update(target_ref, {
                    "views.total_views": firestore.Increment(1),
                    "views.weekly_views": 1,
                    "views.year": cur_year,
                    "views.week": cur_week,
                    "views.last_update": now
                })
        else:
            # Phòng trường hợp document target chưa có object views
            batch.set(target_ref, {
                "views": {
                    "total_views": 1,
                    "weekly_views": 1,
                    "last_update": now,
                    "year": cur_year,
                    "week": cur_week
                }
            }, merge=True)

        await batch.commit()

    async def get_top_views(self, target_type: ViewTargetType, limit: int = 10, page: int = 1, top_type: TopType = TopType.ALL_TIME) -> list[CollectionPublic | DiscoverHotel]:
        db = self._get_db()
        target_collection_name = target_type.value
        
        now = datetime.now(timezone.utc)
        iso = now.isocalendar()
        cur_year = iso[0]
        cur_week = iso[1]


        query = db.collection(target_collection_name)
        if target_type == ViewTargetType.COLLECTION:
            query = query.where(filter=FieldFilter("visibility", "==", CollectionVisibility.PUBLIC.value))

        if top_type == TopType.ALL_TIME:
            # Lấy top views theo tổng số lần xem
            query = query.order_by("views.total_views", direction=firestore.Query.DESCENDING)
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

        return results


view_repository = ViewRepository()