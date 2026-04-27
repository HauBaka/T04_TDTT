from repositories.base_repo import BaseRepository

class ConversationRepository(BaseRepository):
    def __init__(self):
        super().__init__("conversations")


    async def create(self, conversation_data: dict) -> dict:
        """Tạo một conversation mới."""
        """Tạo doc hội thoại mới trong collection 'conversations'."""
        doc_ref = self.collection.document()
        conversation_data["id"] = doc_ref.id
        await doc_ref.set(conversation_data)
        return conversation_data
    
    async def get_by_id(self, conversation_id: str) -> dict:
        """Lấy thông tin một conversation theo ID."""
        doc = await self.collection.document(conversation_id).get()
        return doc.to_dict() if doc.exists else {}
    
    async def update(self, conversation_id: str, update_data: dict) -> dict:
        """Cập nhật thông tin một conversation."""
        doc_ref = self.collection.document(conversation_id)
        await doc_ref.update(update_data)
        res = await doc_ref.get()
        return res.to_dict()
    
    async def add_members(self, conversation_id: str, member_uids: list[str]) -> dict:
        """Thêm thành viên vào một conversation."""
        doc_ref = self.collection.document(conversation_id)
        # Sử dụng ArrayUnion để tránh bị trùng lặp UID
        await doc_ref.update({"member_uids": firestore.ArrayUnion(member_uids)})
        res = await doc_ref.get()
        return res.to_dict()
    
    async def remove_members(self, conversation_id: str, member_uids: list[str]) -> dict:
        """Xóa thành viên khỏi một conversation."""
        doc_ref = self.collection.document(conversation_id)
        await doc_ref.update({"member_uids": firestore.ArrayRemove(member_uids)})
        res = await doc_ref.get()
        return res.to_dict()
    
    async def send_message(self, conversation_id: str, message_data: dict) -> dict:
        """Gửi một tin nhắn mới vào một conversation."""
        """Lưu tin nhắn vào sub-collection 'messages' bên trong hội thoại."""
        msg_ref = self.collection.document(conversation_id).collection("messages").document()
        message_data["id"] = msg_ref.id
        await msg_ref.set(message_data)
        return message_data
    
    async def delete_message(self, conversation_id: str, message_id: str) -> dict:
        """Xóa một tin nhắn khỏi một conversation."""
        """Xóa tin nhắn cụ thể theo ID."""
        await self.collection.document(conversation_id).collection("messages").document(message_id).delete()
        return {"id": message_id}

    async def delete(self, conversation_id: str) -> bool:
        """Xóa một conversation."""
        """Xóa hoàn toàn hội thoại."""
        await self.collection.document(conversation_id).delete()
        return True

# --- CÁC HÀM XỬ LÝ SUB-COLLECTION CỦA USER --- (có thể sử dụng đến)

    async def upsert_user_conversation_node(self, uid: str, conversation_id: str, summary_data: dict):
        """Cập nhật hoặc tạo mới bản tóm tắt hội thoại trong users/{uid}/conversations/{id}."""
        user_conv_ref = self.db.collection("users").document(uid).collection("conversations").document(conversation_id)
        await user_conv_ref.set(summary_data, merge=True)

    async def increment_user_unread_count(self, uid: str, conversation_id: str):
        """Tăng số lượng tin nhắn chưa đọc lên 1 đơn vị."""
        user_conv_ref = self.db.collection("users").document(uid).collection("conversations").document(conversation_id)
        await user_conv_ref.update({"unread_count": firestore.Increment(1)})

    async def remove_user_conversation_node(self, uid: str, conversation_id: str):
        """Xóa hội thoại khỏi danh sách của User (khi User rời nhóm)."""
        await self.db.collection("users").document(uid).collection("conversations").document(conversation_id).delete()

conversation_repo = ConversationRepository()