from core.database import get_db

class BaseRepository:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    def _get_db(self):
        return get_db()
    
    @property
    def _collection(self):
        return self._get_db().collection(self.collection_name)

    async def _get_by_id(self, doc_id: str) -> dict | None:
            """Lấy một document theo ID"""
            doc = await self._collection.document(doc_id).get()
            if not doc.exists:
                return None
                
            data = doc.to_dict()
            if data is not None:
                data["id"] = doc.id

            return data

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

    async def _delete(self, doc_id: str) -> bool:
        """Xóa một document"""
        ref = self._collection.document(doc_id)
        doc = await ref.get()
        
        if not doc.exists:
            return False

        await ref.delete()
        return True