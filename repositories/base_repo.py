import asyncio

from core.database import get_db
from google.cloud.firestore_v1.field_path import FieldPath
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.async_document import AsyncDocumentReference
from google.cloud.firestore_v1.base_document import DocumentSnapshot
MAX_IN_QUERY = 30
class BaseRepository:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    @property
    def _db(self):
        return get_db()
    
    @property
    def _collection(self):
        return self._db.collection(self.collection_name)

    async def _get_by_id(self, doc_id: str) -> dict | None:
            """Lấy một document theo ID"""
            doc = await self._collection.document(doc_id).get()
            if not doc.exists:
                return None
                
            data = doc.to_dict()
            if data is not None:
                data["id"] = doc.id

            return data
    
    async def _get_by_ids(self, doc_ids: list[str]) -> list[dict]:
        """Lấy nhiều document theo list ID"""

        if not doc_ids:
            return []

        # Chia nhỏ theo giới hạn Firestore IN query
        chunks = [
            doc_ids[i:i + MAX_IN_QUERY]
            for i in range(0, len(doc_ids), MAX_IN_QUERY)
        ]

        tasks = [
            self._collection.where(
                filter=FieldFilter(
                    FieldPath.document_id(),
                    "in",
                    chunk
                )
            ).get()
            for chunk in chunks
        ]

        query_results = await asyncio.gather(*tasks)

        result = []

        for docs in query_results:
            for doc in docs:
                data = doc.to_dict()

                if data is not None:
                    data["id"] = doc.id
                    result.append(data)

        return result
    
    async def _create(self, data: dict, doc_id: str | None = None) -> str:
        """Tạo document mới. Nếu có doc_id thì dùng, không thì tự generate"""
        if doc_id:
            ref = self._collection.document(doc_id)
        else:
            ref = self._collection.document()
            
        await ref.set(data)
        return ref.id

    async def _update(self, doc_id: str, update_data: dict) -> None:
        """Cập nhật document"""
        await self._collection.document(doc_id).update(update_data)

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
        """Xóa một document"""
        ref = self._collection.document(doc_id)
        doc = await ref.get()
        
        if not doc.exists:
            return False

        await ref.delete()
        return True
    
    @property
    def _current_timestamp(self):
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)