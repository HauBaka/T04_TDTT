import asyncio
from datetime import timedelta

from fastapi import BackgroundTasks

from core.exceptions import (
    AppException,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
)
from repositories.conversation_repo import conversation_repo
from repositories.user_repo import user_repo
from schemas.chatbot_schema import ChatAskRequest
from schemas.conversation_schema import (
    AddMembersRequest,
    ConversationCreateRequest,
    ConversationDocument,
    ConversationMemberDocument,
    ConversationMemberResponse,
    ConversationMessageDocument,
    ConversationMessageResponse,
    ConversationResponse,
    ConversationRole,
    ConversationUpdateRequest,
    SendMessageRequest,
    SystemSendMessageRequest,
    UserConversationSummaryUpdate,
)
from schemas.invitation_schema import (
    InvitationCreateRequest,
    InvitationResponse,
    InvitationType,
)
from schemas.response_schema import ResponseSchema
from services.invitation_service import invitation_service


class ConversationService:
    def __init__(self):
        self.conversation_repository = conversation_repo

    async def create_conversation(
        self, owner_uid: str, request: ConversationCreateRequest
    ) -> ResponseSchema[ConversationResponse]:
        """Tạo một conversation mới."""

        # Gọi Repo tạo Doc gốc trong 'conversations'
        res = await self.conversation_repository.create(owner_uid, request)

        # Gọi Repo thêm chi tiết Owner vào sub-collection 'members'
        res = await self.conversation_repository.add_members(
            res.id, [owner_uid], [ConversationRole.OWNER]
        )
        if not res:
            raise AppException(message="Failed to create conversation", status_code=500)
        # Đồng bộ vào tóm tắt hội thoại của Owner
        summary = UserConversationSummaryUpdate(
            name=res.name,
            description=res.description,
            thumbnail_url=res.thumbnail_url,
            unread_count=0,
        )
        await self.conversation_repository.upsert_user_conversation_summary(
            owner_uid, res.id, summary
        )

        return ResponseSchema(data=await self._build_response(res))

    async def get_conversation(
        self, conversation_id: str, requester_uid: str
    ) -> ResponseSchema[ConversationResponse]:
        """Lấy thông tin một conversation theo ID."""
        # Lấy thông tin một conversation theo ID
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if not conv:
            raise NotFoundError(message="Conversation not found")
        if requester_uid not in conv.member_uids:
            raise PermissionDeniedError(
                message="You do not have permission to access this conversation"
            )
        return ResponseSchema(data=await self._build_response(conv))

    async def update_conversation(
        self,
        conversation_id: str,
        requester_uid: str,
        update_req: ConversationUpdateRequest,
        background_tasks: BackgroundTasks,
    ) -> ResponseSchema[ConversationResponse]:
        """Cập nhật thông tin một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)

        if requester_uid not in conv.member_uids:
            raise PermissionDeniedError(
                message="You do not have permission to update this conversation"
            )

        if not update_req.model_dump(mode="python", exclude_none=True):
            raise AppException(message="No valid fields to update", status_code=400)

        updated_res = await self.conversation_repository.update(
            conversation_id, update_req
        )

        # Đồng bộ tên/ảnh mới cho tóm tắt hội thoại của tất cả thành viên
        user_summary_update = UserConversationSummaryUpdate.model_validate(
            update_req.model_dump(mode="python", exclude_none=True)
        )
        for uid in conv.member_uids:  # chạy ngầm task này
            background_tasks.add_task(
                self.conversation_repository.upsert_user_conversation_summary,
                uid,
                conversation_id,
                user_summary_update,
            )

        return ResponseSchema(data=await self._build_response(updated_res))

    async def delete_conversation(
        self,
        conversation_id: str,
        requester_uid: str,
        background_tasks: BackgroundTasks,
    ) -> ResponseSchema[bool]:
        """Xóa một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)

        if conv.owner_uid != requester_uid:
            raise PermissionDeniedError(
                message="Only the owner can delete this conversation"
            )

        # Đảm bảo xóa hết summary trước khi xóa chat gốc + sub-collection
        await asyncio.gather(
            *[
                self.conversation_repository.remove_user_conversation_summary(
                    uid, conversation_id
                )
                for uid in conv.member_uids
            ]
        )

        # Thực hiện xóa đoạn chat gốc trong collection 'conversations'
        await self.conversation_repository.delete(conversation_id)
        return ResponseSchema(data=True)

    async def send_invitations(
        self, conversation_id: str, requester_uid: str, target_uids: list[str]
    ) -> ResponseSchema[list[InvitationResponse]]:
        conv = await self.conversation_repository.get_by_id(conversation_id)

        if requester_uid not in conv.member_uids:
            raise PermissionDeniedError(
                message="You are not a member of this conversation"
            )

        if target_uids:
            existing_users = await user_repo.get_users(target_uids)
            existing_uids = set(existing_users.keys())
            not_found_uids = [uid for uid in target_uids if uid not in existing_uids]
            if not_found_uids:
                raise NotFoundError(
                    message=f"Target users not found: {', '.join(not_found_uids)}"
                )

        existing_uids = set(conv.member_uids)

        new_uids = [uid for uid in target_uids if uid not in existing_uids]

        if not new_uids:
            raise BadRequestError(
                message="All provided UIDs are already members of the conversation"
            )

        expired_at = self.conversation_repository._current_timestamp + timedelta(days=7)
        invitation = await invitation_service.send_batch_invitations(
            [
                InvitationCreateRequest(
                    sender_uid=requester_uid,
                    target_uid=uid,
                    type=InvitationType.CONVERSATION,
                    ref_id=conversation_id,
                    expired_at=expired_at,
                )
                for uid in new_uids
            ]
        )

        return ResponseSchema(data=invitation)

    async def add_members_to_conversation(
        self,
        conversation_id: str,
        requester_uid: str,
        request: AddMembersRequest,
        background_tasks: BackgroundTasks,
    ) -> ResponseSchema[ConversationResponse]:
        """Thêm nhiều thành viên vào một conversation."""
        await self.send_invitations(
            conversation_id=conversation_id,
            requester_uid=requester_uid,
            target_uids=request.member_uids,
        )
        conv = await self.conversation_repository.get_by_id(conversation_id)

        # if requester_uid not in conv.member_uids:
        #     raise PermissionDeniedError(message="You are not a member of this conversation")

        # Lọc ra những UID đã tồn tại trong conversation để tránh lỗi khi thêm trùng lặp
        # existing_uids = set(conv.member_uids)
        # new_uids = [uid for uid in request.member_uids if uid not in existing_uids]
        # if not new_uids:
        #     raise BadRequestError(message="All provided UIDs are already members of the conversation")

        # Gọi Repo cập nhật mảng member_uids + thêm vào sub-collection members
        # updated_conv = await self.conversation_repository.add_members(conversation_id, request.member_uids, [ConversationRole.MEMBER] * len(request.member_uids))

        # Tạo tóm tắt hội thoại cho những thành viên mới này
        # summary = UserConversationSummaryUpdate(
        #    name=updated_conv.name,
        #    description=updated_conv.description,
        #    thumbnail_url=updated_conv.thumbnail_url,
        #    unread_count=0,
        #    latest_msg=None
        # )
        # for uid in new_uids: # chạy ngầm task này
        #     background_tasks.add_task(
        #         self.conversation_repository.upsert_user_conversation_summary,
        #         uid, conversation_id, summary
        #     )

        return ResponseSchema(data=await self._build_response(conv))

    async def add_accepted_member(
        self, conversation_id: str, new_uid: str, background_tasks: BackgroundTasks
    ) -> ResponseSchema[ConversationResponse]:
        """Thêm thành viên vào conversation sau khi họ chấp nhận lời mời."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if new_uid in conv.member_uids:
            raise BadRequestError(
                message="You are already a member of this conversation"
            )

        updated_conv = await self.conversation_repository.add_members(
            conversation_id, [new_uid], [ConversationRole.MEMBER]
        )

        # Tạo tóm tắt hội thoại cho thành viên mới này
        summary = UserConversationSummaryUpdate(
            name=updated_conv.name,
            description=updated_conv.description,
            thumbnail_url=updated_conv.thumbnail_url,
            unread_count=0,
            latest_msg=None,
        )
        background_tasks.add_task(
            self.conversation_repository.upsert_user_conversation_summary,
            new_uid,
            conversation_id,
            summary,
        )

        return ResponseSchema(data=await self._build_response(updated_conv))

    async def get_members_from_conversation(
        self, conversation_id: str, requester_uid: str
    ) -> ResponseSchema[list[ConversationMemberResponse]]:
        """Lấy danh sách chi tiết thành viên từ một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)

        if requester_uid not in conv.member_uids:
            raise PermissionDeniedError(
                message="You are not a member of this conversation"
            )

        return ResponseSchema(
            data=await self.conversation_repository.get_detailed_members(
                conversation_id
            )
        )

    async def remove_members_from_conversation(
        self, conversation_id: str, requester_uid: str, target_uids: list[str]
    ) -> ResponseSchema[ConversationResponse]:
        """Xóa nhiều thành viên khỏi một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)

        if conv.owner_uid != requester_uid and not (
            len(target_uids) == 1 and target_uids[0] == requester_uid
        ):
            raise PermissionDeniedError(
                message="You do not have permission to remove members from this conversation"
            )

        if conv.owner_uid in target_uids:
            raise PermissionDeniedError(
                message="Owner cannot be removed from the conversation"
            )

        if "chatbot_system" in target_uids:
            raise PermissionDeniedError(
                message="System member cannot be removed from the conversation"
            )

        # Lọc ra những UID không tồn tại trong conversation để tránh lỗi khi xóa
        existing_uids = set(conv.member_uids)
        valid_target_uids = [uid for uid in target_uids if uid in existing_uids]
        if not valid_target_uids:
            raise BadRequestError(
                message="None of the provided UIDs are members of the conversation"
            )

        # Xóa khỏi conversation
        updated_conv = await self.conversation_repository.remove_members(
            conversation_id, valid_target_uids
        )

        # Xóa tóm tắt hội thoại của những người bị xóa
        await asyncio.gather(
            *[
                self.conversation_repository.remove_user_conversation_summary(
                    uid, conversation_id
                )
                for uid in valid_target_uids
            ]
        )

        return ResponseSchema(data=await self._build_response(updated_conv))

    async def send_message_to_conversation(
        self,
        conversation_id: str,
        requester_uid: str,
        message_data: SendMessageRequest,
        background_tasks: BackgroundTasks,
    ) -> ResponseSchema[ConversationMessageResponse]:
        """Gửi một tin nhắn mới vào một conversation."""
        """Cập nhật số tin nhắn chưa đọc của các thành viên khác trong nhóm."""
        sender, member, conv = await asyncio.gather(
            user_repo.get_user(requester_uid),
            self.conversation_repository.get_member(conversation_id, requester_uid),
            self.conversation_repository.get_by_id(conversation_id),
        )

        if requester_uid not in conv.member_uids:
            raise PermissionDeniedError(
                message="You are not a member of this conversation"
            )

        # Lưu tin nhắn vào Firestore
        saved_msg = await self.conversation_repository.send_message(
            conversation_id, requester_uid, message_data
        )

        # Vòng lặp cập nhật tóm tắt hội thoại cho TẤT CẢ mọi người trong nhóm
        for uid in conv.member_uids:  # chạy ngầm task này
            summary_update = UserConversationSummaryUpdate(latest_msg=saved_msg)
            background_tasks.add_task(
                self.conversation_repository.upsert_user_conversation_summary,
                uid,
                conversation_id,
                summary_update,
            )
            # Nếu người trong vòng lặp không phải là người gửi, tăng số tin chưa đọc lên 1
            if uid != requester_uid:
                background_tasks.add_task(
                    self.conversation_repository.increment_user_unread_count,
                    uid,
                    conversation_id,
                )
            if uid == "chatbot_system":
                background_tasks.add_task(
                    self.send_message_to_chatbot, requester_uid, message_data
                )

        return ResponseSchema(
            data=ConversationMessageResponse(
                id=saved_msg.id,
                sender=ConversationMemberResponse(
                    uid=sender.uid,
                    username=sender.username,
                    display_name=sender.display_name,
                    avatar_url=sender.avatar_url,
                    role=member.role,
                    joined_at=member.joined_at,
                ),
                content=saved_msg.content,
                sent_at=saved_msg.sent_at,
                attachments=saved_msg.attachments,
            )
        )

    async def send_message_to_chatbot(
        self, requester_uid: str, message_data: SendMessageRequest
    ):
        """Hàm này sẽ được gọi từ service của chatbot khi cần gửi tin nhắn vào conversation chatbot của user."""
        from services.chatbot_service import chatbot_service

        ans = await chatbot_service.ask(
            requester_uid=requester_uid,
            ask_request=ChatAskRequest(message=message_data.content),
        )

        message = SystemSendMessageRequest(
            content=ans.data.payload
            if ans.data and ans.data.payload
            else "Hệ thống hiện đang gặp sự cố, vui lòng thử lại sau."
        )

        await self.conversation_repository.send_message(
            conversation_id=f"chatbot_conv_{requester_uid}",
            sender_uid="chatbot_system",
            message_data=message,
        )

        pass

    async def delete_message_from_conversation(
        self, conversation_id: str, message_id: str, requester_uid: str
    ) -> ResponseSchema[bool]:
        """Xóa một tin nhắn khỏi một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        msg = await self.conversation_repository.get_message_by_id(
            conversation_id, message_id
        )

        # Cho phép người gửi xóa tin của chính họ hoặc quản trị viên xóa
        if msg.sender_uid != requester_uid and conv.owner_uid != requester_uid:
            raise PermissionDeniedError(
                message="You do not have permission to delete this message"
            )

        await self.conversation_repository.delete_message(conversation_id, message_id)

        return ResponseSchema(data=True)

    async def get_or_create_default_chatbot_conversation(
        self, uid: str
    ) -> ResponseSchema[ConversationResponse]:
        """Lấy conversation mặc định cho chatbot của user, nếu chưa có thì tạo mới."""
        # Định nghĩa ID cố định cho cuộc hội thoại chatbot của User này
        chatbot_conv_id = f"chatbot_conv_{uid}"
        # Thử lấy hội thoại từ Database
        try:
            conv = await self.conversation_repository.get_by_id(chatbot_conv_id)
        except NotFoundError:
            new_conv = ConversationCreateRequest(
                name="Trợ lý AI", description="Trợ lý AI cá nhân của bạn"
            )
            conv = await self.conversation_repository.create(
                uid, new_conv, custom_id=chatbot_conv_id
            )
            conv = await self.conversation_repository.add_members(
                conv.id, [uid, "chatbot_system"]
            )
            if not conv:
                raise AppException(
                    message="Failed to create default chatbot conversation",
                    status_code=500,
                )

        return ResponseSchema(data=await self._build_response(conv))

    async def get_recent_messages(
        self, conversation_id: str, limit: int = 20
    ) -> ResponseSchema[list[ConversationMessageDocument]]:
        """Lấy danh sách tin nhắn gần đây nhất của một conversation."""
        conv = await self.conversation_repository.get_by_id(conversation_id)

        messages = await self.conversation_repository.get_recent_messages(
            conv.id, limit
        )
        return ResponseSchema(data=messages)

    async def mark_conversation_as_read(
        self, conversation_id: str, requester_uid: str
    ) -> ResponseSchema[bool]:
        """Dùng để FE gọi khi user click vào chat."""
        conv = await self.conversation_repository.get_by_id(conversation_id)

        await self.conversation_repository.reset_user_unread_count(
            requester_uid, conv.id
        )
        return ResponseSchema(data=True)

    async def _get_members_list(
        self, conversation_id: str
    ) -> list[ConversationMemberDocument]:
        """Lấy sub-collection members và map sang Object Schema."""
        # Gọi hàm get_members trong Repo
        return await self.conversation_repository.get_members(conversation_id)

    async def _build_response(
        self, conv_doc: ConversationDocument
    ) -> ConversationResponse:
        """Hàm tiện ích để map dữ liệu thô từ DB sang Schema trả về cho API."""
        return ConversationResponse(
            id=conv_doc.id,
            owner_uid=conv_doc.owner_uid,
            name=conv_doc.name,
            description=conv_doc.description,
            thumbnail_url=conv_doc.thumbnail_url,
            created_at=conv_doc.created_at,
            updated_at=conv_doc.updated_at,
            member_count=len(conv_doc.member_uids),
        )


conversation_service = ConversationService()
