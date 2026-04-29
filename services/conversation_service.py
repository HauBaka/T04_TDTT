
from datetime import datetime
from fastapi import HTTPException

from repositories.conversation_repo import conversation_repo
from schemas.conversation_schema import ConversationResponse, ConversationCreateRequest, ConversationUpdateRequest, AddMembersRequest, SendMessageRequest
from schemas.response_schema import ResponseSchema


class ConversationService:
    def __init__(self):
        self.conversation_repository = conversation_repo

    async def create_conversation(self, owner_uid: str, conversation_data: dict) -> ResponseSchema[ConversationResponse]:
        """Tạo một conversation mới."""
        conversation_data["owner_uid"] = owner_uid
        conversation_data["member_uids"] = [owner_uid]
        conversation_data["created_at"] = datetime.now()
        conversation_data["updated_at"] = datetime.now()
        
        # Gọi Repo tạo Doc gốc trong 'conversations'
        res = await self.conversation_repository.create(conversation_data)
        
        # Gọi Repo thêm chi tiết Owner vào sub-collection 'members'
        await self.conversation_repository.add_members(res["id"], [owner_uid])
        
        # Đồng bộ vào tóm tắt hội thoại của Owner
        summary = {
            "id": res["id"],
            "name": res["name"],
            "unread_count": 0,
            "updated_at": datetime.now()
        }
        await self.conversation_repository.upsert_user_conversation_summary(owner_uid, res["id"], summary)
        
        return ResponseSchema(data=ConversationResponse(**res))
    
    async def get_conversation(self, conversation_id: str, requester_uid: str | None) -> ResponseSchema[ConversationResponse]:
        """Lấy thông tin một conversation theo ID."""
        # Lấy thông tin một conversation theo ID
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Hội thoại không tồn tại")
        if requester_uid and requester_uid not in conv.get("member_uids", []):
            raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập hội thoại này")
        

        return ResponseSchema(data=ConversationResponse(
                id=conversation_id, 
                owner_uid=conv["owner_uid"], 
                name=conv["name"], 
                description=conv["description"], 
                thumbnail_url=conv.get("thumbnail_url"), 
                created_at=conv["created_at"], 
                updated_at=conv["updated_at"], 
                members=conv.get("member_uids", []))
            )
    
    async def update_conversation(self, conversation_id: str, requester_uid: str, update_data: dict) -> ResponseSchema[ConversationResponse]:
        """Cập nhật thông tin một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Hội thoại không tồn tại")
        if requester_uid and requester_uid not in conv.get("member_uids", []):
            raise HTTPException(status_code=403, detail="Bạn không có quyền chỉnh sửa hội thoại này")
        updated_res = await self.conversation_repository.update(conversation_id, update_data)
        # Đồng bộ tên/ảnh mới cho tóm tắt hội thoại của tất cả thành viên
        for uid in conv.get("member_uids", []):
            await self.conversation_repository.upsert_user_conversation_summary(uid, conversation_id, update_data)

        return ResponseSchema(data=ConversationResponse(
                id=conversation_id, 
                owner_uid=conv["owner_uid"], 
                name=update_data.get("name", conv["name"]), 
                description=update_data.get("description", conv["description"]), 
                thumbnail_url=update_data.get("thumbnail_url", conv.get("thumbnail_url")), 
                created_at=conv["created_at"], 
                updated_at=datetime.now(), 
                members=conv.get("member_uids", []))
            )
    
    async def delete_conversation(self, conversation_id: str, requester_uid: str) -> ResponseSchema[bool]:
        """Xóa một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Hội thoại không tồn tại")
        if conv.get("owner_uid") != requester_uid:
            raise HTTPException(status_code=403, detail="Chỉ có quản trị viên mới được xóa hội thoại này")

        member_uids = conv.get("member_uids", [])
        for uid in member_uids:
            # Gọi hàm xóa sub-collection conversations của từng User
            await self.conversation_repository.remove_user_conversation_summary(uid, conversation_id)
            
        # Thực hiện xóa đoạn chat gốc trong collection 'conversations'
        await self.conversation_repository.delete(conversation_id)
        return ResponseSchema(data=True)
    
    async def add_members_to_conversation(self, conversation_id: str, requester_uid: str, request: AddMembersRequest) -> ResponseSchema[ConversationResponse]:
        """Thêm nhiều thành viên vào một conversation."""
        """Xóa một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Hội thoại không tồn tại")
        if requester_uid and requester_uid not in conv.get("member_uids", []):
            raise HTTPException(status_code=403, detail="Thành viên nhóm mới có thể thêm người khác vào chat")
        
        # Gọi Repo cập nhật mảng + thêm sub-collection members
        updated_conv = await self.conversation_repository.add_members(conversation_id, request.member_uids)
        
        # Tạo tóm tắt hội thoại cho những thành viên mới này
        summary = {
            "id": conversation_id,
            "name": conv.get("name"),
            "unread_count": 0,
            "updated_at": datetime.now()
        }
        for uid in request.member_uids:
            await self.conversation_repository.upsert_user_conversation_summary(uid, conversation_id, summary)
        return ResponseSchema(data=ConversationResponse(
                id=conversation_id, 
                owner_uid=conv["owner_uid"], 
                name=conv["name"], 
                description=conv["description"], 
                thumbnail_url=conv.get("thumbnail_url"), 
                created_at=conv["created_at"], 
                updated_at=datetime.now(), 
                members=conv.get("member_uids", []))
            )
    
    async def remove_members_from_conversation(self, conversation_id: str, requester_uid: str, target_uids: list[str]) -> ResponseSchema[ConversationResponse]:
        """Xóa nhiều thành viên khỏi một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Hội thoại không tồn tại")

        if conv.get("owner_uid") != requester_uid:
            raise HTTPException(status_code=403, detail="Chỉ quản trị viên mới có quyền xóa thành viên")

        # Xóa khỏi conversation
        updated_conv = await self.conversation_repository.remove_members(conversation_id, target_uids)
        
        # Xóa tóm tắt hội thoại của những người bị xóa
        for uid in target_uids:
            await self.conversation_repository.remove_user_conversation_summary(uid, conversation_id)
        return ResponseSchema(data=ConversationResponse(
                id=conversation_id, 
                owner_uid=conv["owner_uid"], 
                name=conv["name"], 
                description=conv["description"], 
                thumbnail_url=conv.get("thumbnail_url"), 
                created_at=conv["created_at"], 
                updated_at=datetime.now(), 
                members=conv.get("member_uids", []))
            )
    
    async def send_message_to_conversation(self, conversation_id: str, requester_uid: str, message_data: SendMessageRequest) -> ResponseSchema[ConversationResponse]:
        """Gửi một tin nhắn mới vào một conversation."""
        """Cập nhật số tin nhắn chưa đọc của các thành viên khác trong nhóm."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        member_uids = conv.get("member_uids", [])
        
        if not conv:
            raise HTTPException(status_code=404, detail="Hội thoại không tồn tại")

        if requester_uid not in member_uids:
            raise HTTPException(status_code=403, detail="Bạn không phải thành viên nhóm này")

        # Chuyển Schema thành dict và thêm thông tin người gửi
        msg_data = message_data.model_dump()
        msg_data["sender_uid"] = requester_uid
        msg_data["sent_at"] = datetime.now()

        # Lưu tin nhắn vào Firestore
        saved_msg = await self.conversation_repository.send_message(conversation_id, msg_data)

        # Chuẩn bị bản tóm tắt tin nhắn cuối cùng
        last_msg_summary = {
            "id": saved_msg["id"],
            "content": saved_msg["content"],
            "sender_uid": requester_uid,
            "sent_at": saved_msg["sent_at"]
        }

        # Vòng lặp cập nhật tóm tắt hội thoại cho TẤT CẢ mọi người trong nhóm
        for uid in member_uids:
            await self.conversation_repository.upsert_user_conversation_summary(uid, conversation_id, {
                "latest_msg": last_msg_summary,
                "updated_at": datetime.now()
            })
            
            # Nếu người trong vòng lặp không phải là người gửi, tăng số tin chưa đọc lên 1
            if uid != requester_uid:
                await self.conversation_repository.increment_user_unread_count(uid, conversation_id)
        return ResponseSchema(data=ConversationResponse(
                id=conversation_id, 
                owner_uid=conv["owner_uid"], 
                name=conv["name"], 
                description=conv["description"], 
                thumbnail_url=conv.get("thumbnail_url"), 
                created_at=conv["created_at"], 
                updated_at=datetime.now(), 
                members=conv.get("member_uids", []))
            )

    async def delete_message_from_conversation(self, conversation_id: str, message_id: str, requester_uid: str) -> ResponseSchema[ConversationResponse]:
        """Xóa một tin nhắn khỏi một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        member_uids = conv.get("member_uids", [])
        msg = await self.conversation_repository.get_message_by_id(conversation_id, message_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Hội thoại không tồn tại")
        
        # Cho phép người gửi xóa tin của chính họ hoặc quản trị viên xóa
        if msg.get("sender_uid") != requester_uid and conv.get("owner_uid") != requester_uid:
            raise HTTPException(status_code=403, detail="Bạn không có quyền xóa tin nhắn này")
        await self.conversation_repository.delete_message(conversation_id, message_id)
        return ResponseSchema(data=ConversationResponse(
                id=conversation_id, 
                owner_uid=conv["owner_uid"], 
                name=conv["name"], 
                description=conv["description"], 
                thumbnail_url=conv.get("thumbnail_url"), 
                created_at=conv["created_at"], 
                updated_at=datetime.now(), 
                members=conv.get("member_uids", []))
            )
    
    async def get_or_create_default_chatbot_conversation(self, uid: str) -> ResponseSchema[ConversationResponse]:
        """Lấy conversation mặc định cho chatbot của user, nếu chưa có thì tạo mới."""
        # Định nghĩa ID cố định cho cuộc hội thoại chatbot của User này
        chatbot_conv_id = f"chatbot_conv_{uid}"
        
        # Thử lấy hội thoại từ Database
        conv = await self.conversation_repository.get_by_id(chatbot_conv_id)
        if not conv:
            new_data = {
                "id": f"chatbot_conv_{uid}",
                "owner_uid": uid,
                "name": "Chatbot Assistant",
                "description": "Default chatbot conversation",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "member_uids": [uid]
            }
            await self.conversation_repository.create(new_data)


        return ResponseSchema(data=ConversationResponse(
            id = f"chatbot_conv_{uid}",
            owner_uid = uid,
            name = "Chatbot Assistant",
            description = "Default chatbot conversation",
            created_at = datetime.now(),
            updated_at = datetime.now(),
            members = [uid])
        )
    
    async def get_recent_messages(self, conversation_id: str, limit: int = 20) -> ResponseSchema[list]:
        """Lấy danh sách tin nhắn gần đây nhất của một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Hội thoại không tồn tại")
        
        messages = await self.conversation_repository.get_recent_messages(conversation_id, limit)
        return ResponseSchema(data=messages)

    async def mark_conversation_as_read(self, conversation_id: str, requester_uid: str) -> ResponseSchema[bool]:
        """Dùng để FE gọi khi user click vào chat."""
        await self.conversation_repository.reset_user_unread_count(requester_uid, conversation_id)
        return ResponseSchema(data=True)
    


conversation_service = ConversationService()