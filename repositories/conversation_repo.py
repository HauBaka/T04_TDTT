from repositories.base_repo import BaseRepository
from datetime import datetime, timezone
from google.cloud import firestore

from schemas.conversation_schema import ConversationRole

class ConversationRepository(BaseRepository):
    def __init__(self):
        super().__init__("conversations")


    async def create(self, conversation_data: dict) -> dict:
        """Tạo doc hội thoại mới trong collection 'conversations'."""
        doc_ref = self._collection.document()
        conversation_data["id"] = doc_ref.id
        await doc_ref.set(conversation_data)
        return conversation_data
    
    async def get_by_id(self, conversation_id: str) -> dict | None:
        """Lấy thông tin một conversation theo ID."""
        doc = await self._collection.document(conversation_id).get()
        return doc.to_dict() if doc.exists else {}
    
    async def update(self, conversation_id: str, update_data: dict) -> dict | None:
        """Cập nhật thông tin một conversation."""
        doc_ref = self._collection.document(conversation_id)
        update_data["updated_at"] = datetime.now(timezone.utc)
        await doc_ref.update(update_data)
        res = await doc_ref.get()
        return res.to_dict()
    

    async def add_members(self, conversation_id: str, member_uids: list[str], roles: list[ConversationRole] | None = None) -> dict | None:
        """Thêm thành viên vào một conversation."""
        doc_ref = self._collection.document(conversation_id)
        batch = self._get_db().batch()
        # Sử dụng ArrayUnion để tránh bị trùng lặp UID
        batch.update(doc_ref, {"member_uids": firestore.ArrayUnion(member_uids)})

        # Vòng lặp để tạo các bản thông tin cơ bản user
        for i, uid in enumerate(member_uids):
            member_detail = {
                "uid": uid,
                "joined_at": datetime.now(timezone.utc),
                "role": roles[i].value if roles and i < len(roles) else ConversationRole.MEMBER.value
            }
            
            member_ref = doc_ref.collection("members").document(uid)
            # Bỏ lệnh tạo doc con vào batch
            batch.set(member_ref, member_detail)

        # Gửi toàn bộ cái batch đi
        await batch.commit() 
        
        res = await doc_ref.get()
        return res.to_dict()    
    
    async def remove_members(self, conversation_id: str, member_uids: list[str]) -> dict | None:
        """Xóa thành viên khỏi một conversation."""
        doc_ref = self._collection.document(conversation_id)
        batch = self._get_db().batch()
        # Xóa khỏi mảng và xóa khỏi sub-collection
        batch.update(doc_ref, {"member_uids": firestore.ArrayRemove(member_uids)})
        for uid in member_uids:
            batch.delete(doc_ref.collection("members").document(uid))
        
        await batch.commit()
        res = await doc_ref.get()
        return res.to_dict()
    
    async def send_message(self, conversation_id: str, message_data: dict) -> dict:
        """Gửi một tin nhắn mới vào một conversation."""
        """Lưu tin nhắn vào sub-collection 'messages' bên trong hội thoại."""
        msg_ref = self._collection.document(conversation_id).collection("messages").document()
        message_data["id"] = msg_ref.id
        await msg_ref.set(message_data)
        return message_data
    
    async def delete_message(self, conversation_id: str, message_id: str) -> bool:
        """Xóa một tin nhắn khỏi một conversation."""
        """Xóa tin nhắn cụ thể theo ID."""
        try:
            await self._collection.document(conversation_id).collection("messages").document(message_id).delete()
            return True
        except Exception:
            return False

    # async def _delete_subcollection(self, collection_ref, batch_size: int = 100):
    #     """Hàm đệ quy xóa các document trong sub-collection."""
    #     docs = collection_ref.limit(batch_size).stream() #Lấy ra danh sách các doc nhưng có giới hạn
    #     deleted = 0
    #     async for doc in docs:
    #         await doc.reference.delete()
    #         deleted += 1
    #     if deleted >= batch_size: #Nếu True nghĩa là có khả năng vẫn còn doc
    #         await self._delete_subcollection(collection_ref, batch_size)

    async def delete(self, conversation_id: str) -> bool:
        """Xóa một conversation."""
        """Xóa hoàn toàn hội thoại."""
        # Xóa sub-collection members và messages trước khi xóa doc chính
        try:
            conv_ref = self._collection.document(conversation_id)
            # Xóa tin nhắn và thành viên trước
            await self._delete_subcollection(conv_ref.collection("messages"))
            await self._delete_subcollection(conv_ref.collection("members"))
            # Xóa doc chính
            await conv_ref.delete()
            return True
        except Exception:
            return False
    
    async def get_recent_messages(self, conversation_id: str, limit: int = 20) -> list[dict]:
        """Lấy một số tin nhắn gần đây nhất của một conversation."""
        messages_ref = self._collection.document(conversation_id).collection("messages")
        query = messages_ref.order_by("sent_at", direction=firestore.Query.DESCENDING).limit(limit)
        messages = await query.get()
        return [msg.to_dict() for msg in messages]

    async def get_message_by_id(self, conversation_id: str, message_id: str) -> dict | None:
        doc = await self._get_db().collection("conversations").document(conversation_id)\
                    .collection("messages").document(message_id).get()
        return doc.to_dict() if doc.exists else None
    
    async def get_members(self, conversation_id: str) -> list[dict]:
        members_ref = self._collection.document(conversation_id).collection("members")
        members = await members_ref.get()
        return [member.to_dict() for member in members]
# --- CÁC HÀM XỬ LÝ SUB-COLLECTION CỦA USER --- (có thể sử dụng đến)

    async def upsert_user_conversation_summary(self, uid: str, conversation_id: str, summary_data: dict):
        """Cập nhật hoặc tạo mới bản tóm tắt hội thoại trong users/{uid}/conversations/{id}."""
        user_conv_ref = self._get_db().collection("users").document(uid).collection("conversations").document(conversation_id)
        await user_conv_ref.set(summary_data, merge=True)

    async def increment_user_unread_count(self, uid: str, conversation_id: str):
        """Tăng số lượng tin nhắn chưa đọc lên 1 đơn vị."""
        user_conv_ref = self._get_db().collection("users").document(uid).collection("conversations").document(conversation_id)
        await user_conv_ref.update({"unread_count": firestore.Increment(1)})

    async def reset_user_unread_count(self, uid: str, conversation_id: str):
        """Trả về 0 nếu đã đọc tin nhắn."""
        user_conv_ref = self._get_db().collection("users").document(uid).collection("conversations").document(conversation_id)
        await user_conv_ref.update({"unread_count": 0})

    async def remove_user_conversation_summary(self, uid: str, conversation_id: str):
        """Xóa hội thoại khỏi danh sách của User (khi User rời nhóm)."""
        await self._get_db().collection("users").document(uid).collection("conversations").document(conversation_id).delete()

conversation_repo = ConversationRepository()