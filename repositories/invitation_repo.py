from repositories.base_repo import BaseRepository
from schemas.invitation_schema import (
    InvitationCreateRequest,
    InvitationDocument,
    InvitationUpdateRequest,
    InvitationStatus
)
from loguru import logger
from pydantic import ValidationError as PydanticValidationError


class InvitationRepository(BaseRepository):
    def __init__(self):
        super().__init__("invitations")

    async def create(self, sender_uid: str, invitation_request: InvitationCreateRequest) -> InvitationDocument:
        """Tạo một lời mời mới."""
        invitation_doc = InvitationDocument(
            id=self._collection.document().id,
            sender_uid=sender_uid,
            target_uid=invitation_request.target_uid,
            type=invitation_request.type,
            ref_id=invitation_request.ref_id,
            status=InvitationStatus.PENDING,
            created_at=self._current_timestamp,
            updated_at=self._current_timestamp,
            expired_at=invitation_request.expired_at
        )
        await self._create(invitation_doc.model_dump(mode = "python", exclude_none=False), doc_id=invitation_doc.id)
        return invitation_doc
    
    async def get_by_id(self, invitation_id: str) -> InvitationDocument:
        """Lấy thông tin một lời mời theo ID."""
        data = await self._get_by_id(invitation_id)
        try:
            return InvitationDocument.model_validate(data)
        except PydanticValidationError as e:
            logger.error(f"Error validating invitation data for {invitation_id}: {str(e)}")
            raise PydanticValidationError(f"Invalid invitation data")

    async def update(self, invitation_id: str, update_request: InvitationUpdateRequest) -> InvitationDocument:
        """Cập nhật thông tin một lời mời."""
        update_data = update_request.model_dump(mode="python", exclude_none=True)
        if not update_data:
            raise ValueError("No valid fields to update.")
        
        update_data["updated_at"] = self._current_timestamp
        await self._update(invitation_id, update_data)
        return await self.get_by_id(invitation_id)

    async def delete(self, invitation_id: str) -> bool:
        """Xóa một lời mời."""
        invitation_ref = self._collection.document(invitation_id)
        await invitation_ref.delete()
        return True
    
invitation_repo = InvitationRepository()