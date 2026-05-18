import asyncio

from core.cache import cache_delete, cache_key
from core.database import get_db
from google.cloud.firestore_v1.field_path import FieldPath
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.async_document import AsyncDocumentReference
from google.cloud.firestore_v1.base_document import DocumentSnapshot
from google.cloud.exceptions import NotFound
from core.exceptions import DatabaseError, NotFoundError, ValidationError

from loguru import logger

MAX_IN_QUERY = 30
BASE_CACHE_TTL_SECONDS = 300
class BaseRepository:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    @property
    def _db(self):
        return get_db()
    
    @property
    def _collection(self):
        return self._db.collection(self.collection_name)
    
    def _build_cache_key(self, prefix: str, identifier: str) -> str:
        return cache_key(self.collection_name, prefix, identifier)

    async def _get_from_cache(self, cache_key: str) -> dict | None:
        from core.cache import cache_get

        cached = await cache_get(cache_key)
        return cached
    
    async def _get_many_from_cache(self, cache_keys: list[str]) -> dict[str, dict | None]:
        from core.cache import cache_mget

        if not cache_keys:
            return {}

        cached_items = await cache_mget(cache_keys)
        return cached_items

    async def _set_in_cache(self, cache_key: str, value: dict) -> None:
        from core.cache import cache_set

        await cache_set(cache_key, value, ttl_seconds=BASE_CACHE_TTL_SECONDS)

    async def _set_many_to_cache(self, items: dict[str, dict]) -> None:
        from core.cache import cache_mset

        if not items:
            return

        await cache_mset(items, ttl_seconds=BASE_CACHE_TTL_SECONDS)

    async def _get_by_id(self, doc_id: str) -> dict:
            """Lấy một document theo ID
            
            Raises:
                NotFoundError: Nếu document không tồn tại hoặc data rỗng
                ValidationError: Nếu doc_id rỗng
            """
            if not doc_id:
                raise ValidationError("Document ID is required")

            # Trước tiên thử lấy từ cache
            key = self._build_cache_key("id", doc_id)
            cached = await self._get_from_cache(key)
            if cached is not None:
                return cached

            # Nếu không có trong cache, lấy từ database
            doc = await self._collection.document(doc_id).get()
            if not doc.exists:
                raise NotFoundError("Document not found")
                
            data = doc.to_dict()
            if data is None:
                raise NotFoundError("Document data is empty")

            data["id"] = doc.id

            # Lưu vào cache
            await self._set_in_cache(key, data)

            return data
    
    async def _get_by_ids(self, doc_ids: list[str]) -> list[dict]:
        """Lấy nhiều document theo list ID

        """
        clean_ids = [
            str(did).strip() 
            for did in doc_ids 
            if did and str(did).strip()
        ]

        if not clean_ids:
            return []

        try:
            # Trước tiên thử lấy từ cache
            cache_keys = [
                self._build_cache_key("id", did) 
                for did in clean_ids
            ]
            
            cached_items = await self._get_many_from_cache(cache_keys)
            result_map = {}
            missing_ids = []

            for did, key in zip(clean_ids, cache_keys):
                cached = cached_items.get(key)
                if cached is not None:
                    result_map[did] = cached
                else:
                    missing_ids.append(did)
            
            if not missing_ids:
                return list(result_map.values())

            cache_payload = {}
            doc_refs = [self._collection.document(did) for did in missing_ids]
            docs = [doc async for doc in self._db.get_all(doc_refs)]
            
            for doc in docs:
                if doc.exists:
                    data = doc.to_dict()
                    if data is not None:
                        data["id"] = doc.id
                        result_map[doc.id] = data
                        cache_payload[self._build_cache_key("id", doc.id)] = data

            if cache_payload:
                await self._set_many_to_cache(cache_payload)

            return [
                result_map[did]
                for did in clean_ids
                if did in result_map
            ]

        except Exception:
            logger.exception("Error in _get_by_ids")
            return []
        
    async def _create(self, data: dict, doc_id: str | None = None) -> str:
        """Tạo document mới. Nếu có doc_id thì dùng, không thì tự generate
        
        Raises:
            ValidationError: Nếu data rỗng
        """
        if not data:
            raise ValidationError("Data for creation cannot be empty")
        
        if doc_id:
            ref = self._collection.document(doc_id)
        else:
            ref = self._collection.document()
            
        data["id"] = ref.id

        await ref.set(data)

        await self._set_in_cache(
                self._build_cache_key("id", ref.id),
                data,
        )

        return ref.id

    async def _update(self, doc_id: str, update_data: dict) -> None:
        """Cập nhật document

        Raises:
            NotFoundError: Nếu document không tồn tại
        """
        try:
            await self._collection.document(doc_id).update(update_data)
            await cache_delete(self._build_cache_key("id", doc_id))
        except NotFound:
            raise NotFoundError()

    async def _delete_subcollection(self, sub_ref) -> None:
        batch = self._db.batch()
        count = 0

        async for doc in sub_ref.stream():
            batch.delete(doc.reference)
            count += 1

            if count == 500:
                await batch.commit()
                batch = self._db.batch()
                count = 0

        if count > 0:
            await batch.commit()

    async def _delete(self, doc_id: str) -> bool:
        """Xóa một document
        
        Raises:
            NotFoundError: Nếu document không tồn tại
            ValidationError: Nếu doc_id rỗng
        """
        if not doc_id:
            raise ValidationError("Document ID is required")

        ref = self._collection.document(doc_id)
        doc = await ref.get()
        
        if not doc.exists:
            raise NotFoundError("Document not found")

        await ref.delete()
        await cache_delete(self._build_cache_key("id", doc_id))
        return True
    
    async def _commit_batch(self, batch, retries=2):
        """ Commit batch với retry mechanism để tăng độ bền khi có lỗi tạm thời
        
        Raises:
            DatabaseError: Nếu commit thất bại sau tất cả retries
            ValidationError: Nếu batch rỗng
        """
        if not batch:
            raise ValidationError("Batch object is required for commit")

        for attempt in range(retries + 1):
            try:
                await batch.commit()
                return
            except Exception as e:
                if attempt < retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))  # backoff
                else:
                    logger.error(f"Failed to commit batch after {retries} retries: {str(e)}")
                    raise DatabaseError("Failed to commit batch to database")

    @property
    def _current_timestamp(self):
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)