from typing import Optional

from google.cloud import firestore
from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import NotFoundError, ValidationError
from repositories.base_repo import BaseRepository
from repositories.user_repo import user_repo
from schemas.conversation_schema import (
    ConversationCreateRequest,
    ConversationDocument,
    ConversationMemberDocument,
    ConversationMemberResponse,
    ConversationMessageDocument,
    ConversationRole,
    ConversationUpdateRequest,
    SendMessageRequest,
    UserConversationSummaryUpdate,
)


class ConversationRepository(BaseRepository):
    def __init__(self):
        super().__init__("conversations")

    async def create(
        self,
        owner_uid: str,
        request: ConversationCreateRequest,
        custom_id: Optional[str] = None,
    ) -> ConversationDocument:
        """Tạo doc hội thoại mới trong collection 'conversations'."""
        conversation_doc = ConversationDocument(
            id=custom_id or self._collection.document().id,
            owner_uid=owner_uid,
            name=request.name,
            description=request.description,
            thumbnail_url=request.thumbnail_url,
            created_at=self._current_timestamp,
            updated_at=self._current_timestamp,
            member_uids=[owner_uid],
        )
        await self._create(
            conversation_doc.model_dump(mode="python", exclude_none=False),
            doc_id=conversation_doc.id,
        )

        return conversation_doc

    async def get_by_id(self, conversation_id: str) -> ConversationDocument:
        """Lấy thông tin một conversation theo ID.

        Raises:
            NotFoundError: Nếu conversation không tồn tại hoặc data rỗng
        """
        data = await self._get_by_id(conversation_id)
        try:
            return ConversationDocument.model_validate(data)

        except PydanticValidationError as e:
            logger.error(
                f"Error validating conversation data for ID {conversation_id}: {str(e)}"
            )
            raise ValidationError("Failed to validate conversation data")

    async def get_by_ids(
        self, conversation_ids: list[str]
    ) -> list[ConversationDocument]:
        """Lấy thông tin nhiều conversation theo danh sách ID."""
        conversations = []
        conversation_docs = await self._get_by_ids(conversation_ids)

        for doc in conversation_docs:
            try:
                conv = ConversationDocument.model_validate(doc)
                conversations.append(conv)
            except PydanticValidationError as e:
                logger.error(
                    f"Error validating conversation data for ID {doc.get('id')}: {str(e)}"
                )
                continue

        return conversations

    async def update(
        self, conversation_id: str, update_request: ConversationUpdateRequest
    ) -> ConversationDocument:
        """Cập nhật thông tin một conversation."""

        update_data = update_request.model_dump(mode="python", exclude_none=True)
        if not update_data:
            raise ValidationError("No valid fields to update")

        update_data["updated_at"] = self._current_timestamp
        await self._update(conversation_id, update_data)

        return await self.get_by_id(conversation_id)

    async def add_members(
        self,
        conversation_id: str,
        member_uids: list[str],
        roles: list[ConversationRole] | None = None,
    ) -> ConversationDocument:
        """Thêm thành viên vào một conversation."""
        doc_ref = self._collection.document(conversation_id)
        batch = self._db.batch()
        # Sử dụng ArrayUnion để tránh bị trùng lặp UID
        batch.update(doc_ref, {"member_uids": firestore.ArrayUnion(member_uids)})
        now = self._current_timestamp
        # Vòng lặp để tạo các bản thông tin cơ bản user
        for i, uid in enumerate(member_uids):
            member = ConversationMemberDocument(
                uid=uid,
                role=ConversationRole(roles[i])
                if roles and i < len(roles)
                else ConversationRole.MEMBER,
                joined_at=now,
            )
            member_ref = doc_ref.collection("members").document(uid)
            # Bỏ lệnh tạo doc con vào batch
            batch.set(member_ref, member.model_dump(mode="python", exclude_none=False))

        # Gửi toàn bộ cái batch đi
        await self._commit_batch(batch)

        return await self.get_by_id(conversation_id)

    async def remove_members(
        self, conversation_id: str, member_uids: list[str]
    ) -> ConversationDocument:
        """Xóa thành viên khỏi một conversation."""
        doc_ref = self._collection.document(conversation_id)
        batch = self._db.batch()
        # Xóa khỏi mảng và xóa khỏi sub-collection
        batch.update(doc_ref, {"member_uids": firestore.ArrayRemove(member_uids)})
        for uid in member_uids:
            batch.delete(doc_ref.collection("members").document(uid))

        await self._commit_batch(batch)

        return await self.get_by_id(conversation_id)

    async def send_message(
        self, conversation_id: str, sender_uid: str, message_data: SendMessageRequest
    ) -> ConversationMessageDocument:
        """Gửi một tin nhắn mới vào một conversation."""
        """Lưu tin nhắn vào sub-collection 'messages' bên trong hội thoại."""
        msg_ref = (
            self._collection.document(conversation_id).collection("messages").document()
        )

        message_doc = ConversationMessageDocument(
            id=msg_ref.id,
            sender_uid=sender_uid,
            content=message_data.content,
            sent_at=self._current_timestamp,
            attachments=message_data.attachments,
        )

        await msg_ref.set(message_doc.model_dump(mode="python", exclude_none=False))
        return message_doc

    async def delete_message(self, conversation_id: str, message_id: str):
        """Xóa một tin nhắn khỏi một conversation."""
        """Xóa tin nhắn cụ thể theo ID."""
        await (
            self._collection.document(conversation_id)
            .collection("messages")
            .document(message_id)
            .delete()
        )

    async def delete(self, conversation_id: str):
        """Xóa một conversation."""
        """Xóa hoàn toàn hội thoại."""
        # Xóa sub-collection members và messages trước khi xóa doc chính
        conv_ref = self._collection.document(conversation_id)
        # Xóa tin nhắn và thành viên trước
        await self._delete_subcollection(conv_ref.collection("messages"))
        await self._delete_subcollection(conv_ref.collection("members"))
        # Xóa doc chính
        await conv_ref.delete()
        return True

    async def get_recent_messages(
        self, conversation_id: str, limit: int = 20
    ) -> list[ConversationMessageDocument]:
        """Lấy một số tin nhắn gần đây nhất của một conversation."""
        messages_ref = self._collection.document(conversation_id).collection("messages")
        query = messages_ref.order_by(
            "sent_at", direction=firestore.Query.DESCENDING
        ).limit(limit)
        messages = await query.get()

        message_list = []
        for msg in messages:
            try:
                message_list.append(
                    ConversationMessageDocument.model_validate(msg.to_dict())
                )
            except PydanticValidationError as e:
                logger.error(
                    f"Error validating message data for ID {msg.id} in conversation {conversation_id}: {str(e)}"
                )
                continue

        return message_list

    async def get_message_by_id(
        self, conversation_id: str, message_id: str
    ) -> ConversationMessageDocument:
        """
        Lấy một tin nhắn cụ thể theo ID trong một conversation.

        Raises:
            NotFoundError: Nếu tin nhắn không tồn tại hoặc data rỗng
            ValidationError: Nếu lỗi trong quá trình validate dữ liệu
        """
        doc = (
            await self._db.collection("conversations")
            .document(conversation_id)
            .collection("messages")
            .document(message_id)
            .get()
        )

        if not doc.exists:
            raise NotFoundError("Message not found")

        try:
            return ConversationMessageDocument.model_validate(doc.to_dict())
        except PydanticValidationError as e:
            logger.error(
                f"Error validating message data for ID {message_id} in conversation {conversation_id}: {str(e)}"
            )
            raise ValidationError("Failed to validate message data for retrieval")

    async def get_member(
        self, conversation_id: str, member_id: str
    ) -> ConversationMemberDocument:
        """Lấy thông tin một thành viên cụ thể trong một conversation."""
        doc = (
            await self._db.collection("conversations")
            .document(conversation_id)
            .collection("members")
            .document(member_id)
            .get()
        )

        if not doc.exists:
            raise NotFoundError("Member not found in this conversation")

        try:
            return ConversationMemberDocument.model_validate(doc.to_dict())
        except PydanticValidationError as e:
            logger.error(
                f"Error validating member data for UID {member_id} in conversation {conversation_id}: {str(e)}"
            )
            raise ValidationError("Failed to validate member data for retrieval")

    async def get_members(
        self, conversation_id: str
    ) -> list[ConversationMemberDocument]:
        members_ref = self._collection.document(conversation_id).collection("members")
        members = await members_ref.get()

        member_list = []
        for member in members:
            try:
                member_list.append(
                    ConversationMemberDocument.model_validate(member.to_dict())
                )
            except PydanticValidationError as e:
                logger.error(
                    f"Error validating member data for conversation {conversation_id}: {str(e)}"
                )
                continue

        return member_list

    async def get_detailed_members(
        self, conversation_id: str
    ) -> list[ConversationMemberResponse]:
        """Lấy thông tin chi tiết của các thành viên trong một conversation."""
        members = await self.get_members(conversation_id)
        member_details = await user_repo.get_users([member.uid for member in members])
        response_members = []
        for member in members:
            user_info = member_details.get(member.uid)
            if not user_info:
                logger.warning(
                    f"User info not found for UID {member.uid} when building conversation member response"
                )
                continue

            response_members.append(
                ConversationMemberResponse(
                    uid=member.uid,
                    username=user_info.username,
                    display_name=user_info.display_name,
                    avatar_url=user_info.avatar_url,
                    role=member.role,
                    joined_at=member.joined_at,
                )
            )
        return response_members

    # --- CÁC HÀM XỬ LÝ SUB-COLLECTION CỦA USER --- (có thể sử dụng đến)

    async def upsert_user_conversation_summary(
        self, uid: str, conversation_id: str, update_req: UserConversationSummaryUpdate
    ):
        """Cập nhật hoặc tạo mới bản tóm tắt hội thoại trong users/{uid}/conversations/{id}."""
        user_conv_ref = (
            self._db.collection("users")
            .document(uid)
            .collection("conversations")
            .document(conversation_id)
        )
        await user_conv_ref.set(update_req.model_dump(exclude_none=True), merge=True)

    async def increment_user_unread_count(self, uid: str, conversation_id: str):
        """Tăng số lượng tin nhắn chưa đọc lên 1 đơn vị."""
        user_conv_ref = (
            self._db.collection("users")
            .document(uid)
            .collection("conversations")
            .document(conversation_id)
        )
        await user_conv_ref.update({"unread_count": firestore.Increment(1)})

    async def reset_user_unread_count(self, uid: str, conversation_id: str):
        """Trả về 0 nếu đã đọc tin nhắn."""
        user_conv_ref = (
            self._db.collection("users")
            .document(uid)
            .collection("conversations")
            .document(conversation_id)
        )
        await user_conv_ref.update({"unread_count": 0})

    async def remove_user_conversation_summary(self, uid: str, conversation_id: str):
        """Xóa hội thoại khỏi danh sách của User (khi User rời nhóm)."""
        await (
            self._db.collection("users")
            .document(uid)
            .collection("conversations")
            .document(conversation_id)
            .delete()
        )


conversation_repo = ConversationRepository()
