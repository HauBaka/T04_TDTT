import asyncio

from core.database import get_db
from google.cloud.exceptions import NotFound
from core.exceptions import DatabaseError, NotFoundError, ValidationError

from loguru import logger

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

    async def _get_by_id(self, doc_id: str) -> dict:
            """Lấy một document theo ID
            
            Raises:
                NotFoundError: Nếu document không tồn tại hoặc data rỗng
                ValidationError: Nếu doc_id rỗng
            """
            if not doc_id:
                raise ValidationError("Document ID is required")

            doc = await self._collection.document(doc_id).get()
            if not doc.exists:
                raise NotFoundError("Document not found")
                
            data = doc.to_dict()
            if data is None:
                raise NotFoundError("Document data is empty")

            data["id"] = doc.id

            return data
    
    async def _get_by_ids(self, doc_ids: list[str]) -> list[dict]:
        """Lấy nhiều document theo list ID

        """
        clean_ids = [str(did).strip() for did in doc_ids if did and str(did).strip()]

        if not clean_ids:
            return []

        try:
            doc_refs = [self._collection.document(did) for did in clean_ids]
            docs = [doc async for doc in self._db.get_all(doc_refs)]
            
            result = []
            for doc in docs:
                if doc.exists:
                    data = doc.to_dict()
                    if data is not None:
                        data["id"] = doc.id
                        result.append(data)
        
            return result

        except Exception as e:
            logger.error(f"Error in _get_by_ids using get_all: {str(e)}")
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
        return ref.id

    async def _update(self, doc_id: str, update_data: dict) -> None:
        """Cập nhật document

        Raises:
            NotFoundError: Nếu document không tồn tại
        """
        try:
            await self._collection.document(doc_id).update(update_data)
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