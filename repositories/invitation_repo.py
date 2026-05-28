from datetime import timedelta, timezone

from google.cloud.firestore_v1.base_query import FieldFilter
from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from repositories.base_repo import BaseRepository
from schemas.invitation_schema import (
    GetPendingInvitationsRequest,
    InvitationCreateRequest,
    InvitationDocument,
    InvitationStatus,
    InvitationUpdateRequest,
)


class InvitationRepository(BaseRepository):
    def __init__(self):
        super().__init__("invitations")

    async def create(
        self, invitation_request: InvitationCreateRequest
    ) -> InvitationDocument:
        """Tạo một lời mời mới."""
        invitation_doc = InvitationDocument(
            id=self._collection.document().id,
            sender_uid=invitation_request.sender_uid,
            target_uid=invitation_request.target_uid,
            type=invitation_request.type,
            ref_id=invitation_request.ref_id,
            status=InvitationStatus.PENDING,
            created_at=self._current_timestamp,
            updated_at=self._current_timestamp,
            expired_at=invitation_request.expired_at,
        )
        await self._create(
            invitation_doc.model_dump(mode="python", exclude_none=False),
            doc_id=invitation_doc.id,
        )
        return invitation_doc

    async def create_batch(
        self, invitation_requests: list[InvitationCreateRequest]
    ) -> list[InvitationDocument]:
        """Tạo nhiều lời mời cùng lúc."""
        if not invitation_requests:
            return []

        batch = self._db.batch()
        invitations = []
        current_timestamp = self._current_timestamp
        for req in invitation_requests:
            doc_ref = self._collection.document()
            # Normalize expired_at to timezone-aware UTC
            expired_at = req.expired_at
            if expired_at is None:
                expired_at = current_timestamp + timedelta(days=7)
            else:
                if expired_at.tzinfo is None:
                    expired_at = expired_at.replace(tzinfo=timezone.utc)
            # Ensure expired_at is in the future
            if expired_at <= current_timestamp:
                expired_at = current_timestamp + timedelta(days=7)

            invitation_doc = InvitationDocument(
                id=doc_ref.id,
                sender_uid=req.sender_uid,
                target_uid=req.target_uid,
                type=req.type,
                ref_id=req.ref_id,
                status=InvitationStatus.PENDING,
                created_at=current_timestamp,
                updated_at=current_timestamp,
                expired_at=expired_at,
            )
            batch.create(
                doc_ref, invitation_doc.model_dump(mode="python", exclude_none=False)
            )
            invitations.append(invitation_doc)

        await self._commit_batch(batch)
        return invitations

    async def get_pending_invitations_for_user(
        self, requests: list[GetPendingInvitationsRequest]
    ) -> dict[str, InvitationDocument]:
        """Lấy tất cả lời mời vẫn còn hiệu lực và lọc chính xác theo từng cặp request."""
        if not requests:
            return {}

        target_uids = list(set(req.target_uid for req in requests))

        valid_request_keys = {
            f"{req.target_uid}_{req.actor_uid}_{req.type.value}_{req.ref_id}"
            for req in requests
        }

        CHUNK_SIZE = 10
        pending_mapping = {}
        for i in range(0, len(target_uids), CHUNK_SIZE):
            chunk = target_uids[i : i + CHUNK_SIZE]
            query = (
                self._collection.where(filter=FieldFilter("target_uid", "in", chunk))
                .where(filter=FieldFilter("status", "==", InvitationStatus.PENDING))
                .where(filter=FieldFilter("expired_at", ">", self._current_timestamp))
            )
            try:
                docs = await query.get()
            except Exception as e:
                logger.error(
                    f"Error querying pending invitations chunk {chunk}: {str(e)}"
                )
                continue

            for doc in docs:
                data = doc.to_dict() or {}
                data["id"] = doc.id
                try:
                    inv_doc = InvitationDocument.model_validate(data)
                    composite_key = f"{inv_doc.target_uid}_{inv_doc.sender_uid}_{inv_doc.type.value}_{inv_doc.ref_id}"
                    if composite_key in valid_request_keys:
                        pending_mapping[composite_key] = inv_doc
                except PydanticValidationError as e:
                    logger.error(
                        f"Error validating invitation data for document {doc.id}: {str(e)}"
                    )
                    continue

        return pending_mapping

    async def get_by_id(self, invitation_id: str) -> InvitationDocument:
        """Lấy thông tin một lời mời theo ID."""
        data = await self._get_by_id(invitation_id)
        try:
            return InvitationDocument.model_validate(data)
        except PydanticValidationError as e:
            logger.error(
                f"Error validating invitation data for {invitation_id}: {str(e)}"
            )
            raise PydanticValidationError("Invalid invitation data")

    async def update(
        self, invitation_id: str, update_request: InvitationUpdateRequest
    ) -> InvitationDocument:
        """Cập nhật thông tin một lời mời."""
        update_data = update_request.model_dump(mode="python", exclude_none=True)
        if not update_data:
            raise ValueError("No valid fields to update.")

        update_data["updated_at"] = self._current_timestamp
        await self._update(invitation_id, update_data)
        return await self.get_by_id(invitation_id)

    async def delete(self, invitation_id: str) -> bool:
        """Xóa một lời mời."""
        await self._delete(invitation_id)
        return True


invitation_repo = InvitationRepository()
