import asyncio
from datetime import datetime, timezone
from fastapi import HTTPException
from fastapi import BackgroundTasks


from repositories.conversation_repo import conversation_repo
from schemas.conversation_schema import ConversationResponse, ConversationCreateRequest, ConversationUpdateRequest, AddMembersRequest, SendMessageRequest, ConversationRole, ConversationMember
from schemas.response_schema import ResponseSchema
from core.exceptions import AppException, NotFoundError, PermissionDeniedError

class ConversationService:
    def __init__(self):
        self.conversation_repository = conversation_repo

    async def create_conversation(self, owner_uid: str, conversation_data: dict) -> ResponseSchema[ConversationResponse]:
        """Tạo một conversation mới."""
        conversation_data["owner_uid"] = owner_uid
        conversation_data["member_uids"] = [owner_uid]
        conversation_data["created_at"] = datetime.now(timezone.utc)
        conversation_data["updated_at"] = datetime.now(timezone.utc)
        
        # Gọi Repo tạo Doc gốc trong 'conversations'
        res = await self.conversation_repository.create(conversation_data)
        
        # Gọi Repo thêm chi tiết Owner vào sub-collection 'members'
        res = await self.conversation_repository.add_members(res["id"], [owner_uid], [ConversationRole.OWNER])
        if not res:
            raise AppException(message="Failed to create conversation", status_code=500)
        # Đồng bộ vào tóm tắt hội thoại của Owner
        summary = {
            "id": res["id"],
            "name": res["name"],
            "unread_count": 0,
            "updated_at": datetime.now(timezone.utc)
        }
        await self.conversation_repository.upsert_user_conversation_summary(owner_uid, res["id"], summary)
        
        return ResponseSchema(data=await self._build_response(res))

    async def get_conversation(self, conversation_id: str, requester_uid: str) -> ResponseSchema[ConversationResponse]:
        """Lấy thông tin một conversation theo ID."""
        # Lấy thông tin một conversation theo ID
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise NotFoundError(message="Conversation not found")
        if requester_uid not in conv.get("member_uids", []):
            raise PermissionDeniedError(message="You do not have permission to access this conversation")
        return ResponseSchema(data=await self._build_response(conv))
    
    async def update_conversation(self, conversation_id: str, requester_uid: str, update_data: dict, background_tasks: BackgroundTasks) -> ResponseSchema[ConversationResponse]:
        """Cập nhật thông tin một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise NotFoundError(message="Conversation not found")
        if requester_uid not in conv.get("member_uids", []):
            raise PermissionDeniedError(message="You do not have permission to update this conversation")
        if not update_data.get("name") and not update_data.get("description") and not update_data.get("thumbnail_url"):
            raise AppException(message="No valid fields to update", status_code=400)

        updated_res = await self.conversation_repository.update(conversation_id, update_data)
        
        if not updated_res:
            raise AppException(message="Failed to update conversation", status_code=500)

        # Đồng bộ tên/ảnh mới cho tóm tắt hội thoại của tất cả thành viên
        for uid in conv.get("member_uids", []): # chạy ngầm task này
            # await self.conversation_repository.upsert_user_conversation_summary(uid, conversation_id, update_data)
            background_tasks.add_task(
                self.conversation_repository.upsert_user_conversation_summary, 
                uid, conversation_id, update_data
            )
        return ResponseSchema(data=await self._build_response(updated_res))
    
    async def delete_conversation(self, conversation_id: str, requester_uid: str, background_tasks: BackgroundTasks) -> ResponseSchema[bool]:
        """Xóa một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise NotFoundError(message="Conversation not found")
        if conv.get("owner_uid") != requester_uid:
            raise PermissionDeniedError(message="Only the owner can delete this conversation")

        member_uids = conv.get("member_uids", [])
        # for uid in member_uids: # chạy ngầm task này
        #     # Gọi hàm xóa sub-collection conversations của từng User
        #     # await self.conversation_repository.remove_user_conversation_summary(uid, conversation_id)
        #     background_tasks.add_task(
        #         self.conversation_repository.remove_user_conversation_summary, uid, conversation_id
        #     )

        # Đảm bảo xóa hết summary trước khi xóa chat gốc + sub-collection
        await asyncio.gather(*[
            self.conversation_repository.remove_user_conversation_summary(uid, conversation_id)
            for uid in member_uids
        ])

        # Thực hiện xóa đoạn chat gốc trong collection 'conversations'
        await self.conversation_repository.delete(conversation_id)
        return ResponseSchema(data=True)
    
    async def add_members_to_conversation(self, conversation_id: str, requester_uid: str, request: AddMembersRequest, background_tasks: BackgroundTasks) -> ResponseSchema[ConversationResponse]:
        """Thêm nhiều thành viên vào một conversation."""
        """Xóa một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise NotFoundError(message="Conversation not found")
        if requester_uid not in conv.get("member_uids", []):
            raise PermissionDeniedError(message="You are not a member of this conversation")

        # Lọc ra những UID đã tồn tại trong conversation để tránh lỗi khi thêm trùng lặp
        existing_uids = set(conv.get("member_uids", []))
        new_uids = [uid for uid in request.member_uids if uid not in existing_uids]
        if not new_uids:
            raise AppException(message="All provided UIDs are already members of the conversation", status_code=400)

        # Gọi Repo cập nhật mảng + thêm sub-collection members
        updated_conv = await self.conversation_repository.add_members(conversation_id, new_uids, [ConversationRole.MEMBER] * len(new_uids))
        if not updated_conv:
            raise AppException(message="Failed to update conversation", status_code=500)
        
        # Tạo tóm tắt hội thoại cho những thành viên mới này
        summary = {
            "id": conversation_id,
            "name": updated_conv.get("name"),
            "unread_count": 0,
            "updated_at": datetime.now(timezone.utc)
        }
        for uid in new_uids: # chạy ngầm task này
            # await self.conversation_repository.upsert_user_conversation_summary(uid, conversation_id, summary)
            background_tasks.add_task(
                self.conversation_repository.upsert_user_conversation_summary, 
                uid, conversation_id, summary
            )
        
        return ResponseSchema(data=await self._build_response(updated_conv))
    
    async def remove_members_from_conversation(self, conversation_id: str, requester_uid: str, target_uids: list[str]) -> ResponseSchema[ConversationResponse]:
        """Xóa nhiều thành viên khỏi một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise NotFoundError(message="Conversation not found")

        if conv.get("owner_uid") != requester_uid:
            raise PermissionDeniedError(message="Only owner can remove members from the conversation")

        if conv.get("owner_uid") in target_uids:
            raise PermissionDeniedError(message="Owner cannot be removed from the conversation")

        # Lọc ra những UID không tồn tại trong conversation để tránh lỗi khi xóa
        existing_uids = set(conv.get("member_uids", []))
        valid_target_uids = [uid for uid in target_uids if uid in existing_uids]
        if not valid_target_uids:
            raise AppException(message="None of the provided UIDs are members of the conversation", status_code=400)

        # Xóa khỏi conversation
        updated_conv = await self.conversation_repository.remove_members(conversation_id, valid_target_uids)
        if not updated_conv:
            raise AppException(message="Failed to update conversation", status_code=500)
        # Xóa tóm tắt hội thoại của những người bị xóa
        await asyncio.gather(*[
            self.conversation_repository.remove_user_conversation_summary(uid, conversation_id)
            for uid in valid_target_uids
        ])
        #for uid in valid_target_uids:
        #    await self.conversation_repository.remove_user_conversation_summary(uid, conversation_id)
        
        return ResponseSchema(data=await self._build_response(updated_conv))
    
    async def send_message_to_conversation(self, conversation_id: str, requester_uid: str, message_data: SendMessageRequest, background_tasks: BackgroundTasks) -> ResponseSchema[ConversationResponse]:
        """Gửi một tin nhắn mới vào một conversation."""
        """Cập nhật số tin nhắn chưa đọc của các thành viên khác trong nhóm."""
        conv = await self.conversation_repository.get_by_id(conversation_id)

        if not conv:
            raise NotFoundError(message="Conversation not found")

        member_uids = conv.get("member_uids", [])

        if requester_uid not in member_uids:
            raise PermissionDeniedError(message="You are not a member of this conversation")

        # Chuyển Schema thành dict và thêm thông tin người gửi
        msg_data = message_data.model_dump()
        msg_data["sender_uid"] = requester_uid
        msg_data["sent_at"] = datetime.now(timezone.utc)

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
        for uid in member_uids: # chạy ngầm task này
            # await self.conversation_repository.upsert_user_conversation_summary(uid, conversation_id, {
            #     "latest_msg": last_msg_summary,
            #     "updated_at": datetime.now(timezone.utc)
            # })
            summary_update = {
                "latest_msg": last_msg_summary,
                "updated_at": datetime.now(timezone.utc)
            }
            background_tasks.add_task(
                self.conversation_repository.upsert_user_conversation_summary,
                uid, conversation_id, summary_update
            )
            # Nếu người trong vòng lặp không phải là người gửi, tăng số tin chưa đọc lên 1
            if uid != requester_uid:
                #await self.conversation_repository.increment_user_unread_count(uid, conversation_id)
                background_tasks.add_task(
                    self.conversation_repository.increment_user_unread_count,
                    uid, conversation_id
                )
        
        return ResponseSchema(data=await self._build_response(conv))


    async def delete_message_from_conversation(self, conversation_id: str, message_id: str, requester_uid: str) -> ResponseSchema[ConversationResponse]:
        """Xóa một tin nhắn khỏi một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise NotFoundError(message="Conversation not found")

        msg = await self.conversation_repository.get_message_by_id(conversation_id, message_id)
        if not msg:
            raise NotFoundError(message="Message not found")
        
        # Cho phép người gửi xóa tin của chính họ hoặc quản trị viên xóa
        if msg.get("sender_uid") != requester_uid and conv.get("owner_uid") != requester_uid:
            raise PermissionDeniedError(message="You do not have permission to delete this message")
        await self.conversation_repository.delete_message(conversation_id, message_id)
        
        return ResponseSchema(data=await self._build_response(conv))

    
    async def get_or_create_default_chatbot_conversation(self, uid: str) -> ResponseSchema[ConversationResponse]:
        """Lấy conversation mặc định cho chatbot của user, nếu chưa có thì tạo mới."""
        # Định nghĩa ID cố định cho cuộc hội thoại chatbot của User này
        chatbot_conv_id = f"chatbot_conv_{uid}"
        now = datetime.now(timezone.utc)
        # Thử lấy hội thoại từ Database
        conv = await self.conversation_repository.get_by_id(chatbot_conv_id)
        if not conv:
            new_data = {
                "id": f"chatbot_conv_{uid}",
                "owner_uid": uid,
                "name": "Chatbot Assistant",
                "description": "Default chatbot conversation",
                "created_at": now,
                "updated_at": now,
                "member_uids": [uid, "chatbot_system"]
            }
            conv = await self.conversation_repository.create(new_data)
            conv = await self.conversation_repository.add_members(conv["id"], [uid, "chatbot_system"])
            if not conv:
                raise AppException(message="Failed to create default chatbot conversation", status_code=500)
            
        return ResponseSchema(data=await self._build_response(conv))
    
    async def get_recent_messages(self, conversation_id: str, limit: int = 20) -> ResponseSchema[list]:
        """Lấy danh sách tin nhắn gần đây nhất của một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise NotFoundError(message="Conversation not found")
        
        messages = await self.conversation_repository.get_recent_messages(conversation_id, limit)
        return ResponseSchema(data=messages)

    async def mark_conversation_as_read(self, conversation_id: str, requester_uid: str) -> ResponseSchema[bool]:
        """Dùng để FE gọi khi user click vào chat."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise NotFoundError(message="Conversation not found")
        
        await self.conversation_repository.reset_user_unread_count(requester_uid, conversation_id)
        return ResponseSchema(data=True)
    
    async def _get_members_list(self, conversation_id: str) -> list[ConversationMember]:
        """Lấy sub-collection members và map sang Object Schema."""
        # Gọi hàm get_members trong Repo
        docs = await self.conversation_repository.get_members(conversation_id)
        return [ConversationMember(**doc) for doc in docs]

    async def _build_response(self, conv_data: dict) -> ConversationResponse:
        """Hàm tiện ích để map dữ liệu thô từ DB sang Schema trả về cho API."""
        member_list = await self._get_members_list(conv_data["id"])
        return ConversationResponse(
            id=conv_data["id"],
            owner_uid=conv_data["owner_uid"],
            name=conv_data["name"],
            description=conv_data.get("description"),
            thumbnail_url=conv_data.get("thumbnail_url"),
            created_at=conv_data["created_at"],
            updated_at=conv_data["updated_at"],
            members=member_list
        )

conversation_service = ConversationService()