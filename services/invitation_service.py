from datetime import datetime, timezone
from core.exceptions import NotFoundError, AppException
from repositories.invitation_repo import invitation_repo
from repositories.user_repo import user_repo
from schemas.invitation_schema import InvitationCreateRequest, InvitationResponse, InvitationStatus, InvitationType, InvitationUpdateRequest
from schemas.response_schema import ResponseSchema
from services.collection_service import collection_service
from repositories.collection_repo import collection_repo

class InvitationService:
    def __init__(self):
        self.invitation_repo = invitation_repo

    async def create_invitation(self, sender_uid: str, invitation_request: InvitationCreateRequest) -> ResponseSchema[InvitationResponse]:
        """Tạo một lời mời mới."""
        # Check target user exists
        target_user = await user_repo.get_user(invitation_request.target_uid)
        if not target_user:
            raise NotFoundError("Target user not found.")
        
        # Check sender user exists
        sender = await user_repo.get_user(sender_uid)
        if not sender:
            raise NotFoundError("Sender user not found.")
        
        # Create invitation data
        invitation_data = {
            "sender_uid": sender_uid,
            "target_uid": invitation_request.target_uid,
            "type": invitation_request.type.value,
            "ref_id": invitation_request.ref_id,
            "status": InvitationStatus.PENDING.value,
            "created_at": datetime.now(timezone.utc),
            "expired_at": invitation_request.expired_at
        }
        
        # Create in database
        invitation_id = await self.invitation_repo.create(invitation_data)
        invitation_data["id"] = invitation_id
            
        return self.build_invitation_response(invitation_data, status_code=201, message="Invitation created successfully")

    async def get_invitation(self, invitation_id: str, requester_uid: str) -> ResponseSchema[InvitationResponse]:
        """Lấy thông tin của một lời mời cụ thể."""
        # Get invitation from database
        invitation = await self.invitation_repo.get_by_id(invitation_id)
        if not invitation:
            raise NotFoundError("Invitation not found.")
        
        # Check permission - only sender or target can view
        if requester_uid != invitation.get("sender_uid") and requester_uid != invitation.get("target_uid"):
            raise AppException(status_code=403, message="You do not have permission to view this invitation.")
        
        return self.build_invitation_response(invitation, status_code=200, message="Invitation retrieved successfully")

    async def update_invitation(self, invitation_id: str, requester_uid: str, invitation_update: InvitationUpdateRequest) -> ResponseSchema[InvitationResponse]:
        """Cập nhật trạng thái của một lời mời cụ thể."""
        # Get invitation from database
        invitation = await self.invitation_repo.get_by_id(invitation_id)
        if not invitation:
            raise NotFoundError("Invitation not found.")
        
        # Check permission - only target user can accept/decline
        if requester_uid != invitation.get("target_uid"):
            raise AppException(status_code=403, message="Only target user can update invitation status.")
        
        # Update status in database
        update_data = {
            "status": invitation_update.status.value
        }
        await self.invitation_repo.update(invitation_id, update_data)
        
        # Get updated invitation
        updated_invitation = await self.invitation_repo.get_by_id(invitation_id)

        if invitation_update.status == InvitationStatus.ACCEPTED:
            if invitation.get("type") == InvitationType.COLLECTION.value:
                await collection_repo.add_collaborators_to_collection(
                    collection_id=updated_invitation.get("ref_id"),
                    requester_id=updated_invitation.get("sender_uid"),
                    collaborator_uids=[requester_uid]
                )

        return self.build_invitation_response(updated_invitation, status_code=200, message="Invitation updated successfully")
    
    async def delete_invitation(self, invitation_id: str, requester_uid: str) -> ResponseSchema[bool]:
        """Xóa một lời mời cụ thể."""
        # Get invitation from database
        invitation = await self.invitation_repo.get_by_id(invitation_id)
        if not invitation:
            raise NotFoundError("Invitation not found.")
        
        # Check permission - only sender or target can delete
        if requester_uid != invitation.get("sender_uid") and requester_uid != invitation.get("target_uid"):
            raise AppException(status_code=403, message="You do not have permission to delete this invitation.")
        
        # Delete from database
        result = await self.invitation_repo.delete(invitation_id)
        
        return ResponseSchema[bool](
            status_code=200,
            message="Invitation deleted successfully",
            data=result
        )
    
    def build_invitation_response(self, invitation_data: dict, status_code: int = 200, message: str = "Success") -> ResponseSchema[InvitationResponse]:
        """Xây dựng response từ invitation data."""
        if not invitation_data:
            raise NotFoundError("Invitation not found.")
        
        invitation = InvitationResponse(
            id=invitation_data.get("id", ""),
            sender_uid=invitation_data.get("sender_uid"),
            target_uid=invitation_data.get("target_uid"),
            type=InvitationType(invitation_data.get("type")),
            ref_id=invitation_data.get("ref_id"),
            status=InvitationStatus(invitation_data.get("status")),
            created_at=invitation_data.get("created_at", datetime.now(timezone.utc)),
            expired_at=invitation_data.get("expired_at")
        )
        return ResponseSchema[InvitationResponse](
            status_code=status_code,
            message=message,
            data=invitation
        )

invitation_service = InvitationService()