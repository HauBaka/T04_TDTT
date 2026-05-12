from fastapi import BackgroundTasks
from datetime import datetime, timezone
from core.exceptions import NotFoundError, AppException
from repositories.invitation_repo import invitation_repo
from repositories.user_repo import user_repo
from schemas.conversation_schema import ConversationRole
from schemas.invitation_schema import InvitationCreateRequest, InvitationResponse, InvitationStatus, InvitationType, InvitationUpdateRequest
from schemas.response_schema import ResponseSchema
from services.collection_service import collection_service
from repositories.collection_repo import collection_repo
from services.conversation_service import conversation_service
from repositories.conversation_repo import conversation_repo

class InvitationService:
    def __init__(self):
        self.invitation_repo = invitation_repo

    async def create_invitation(self, sender_uid: str, invitation_request: InvitationCreateRequest) -> ResponseSchema[InvitationResponse]:
        """Tạo một lời mời mới."""
        users = await user_repo.get_users([sender_uid, invitation_request.target_uid])
        if invitation_request.target_uid not in users:
            raise NotFoundError("Target user not found.")
        if sender_uid not in users:
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

    async def update_invitation(self, invitation_id: str, requester_uid: str, invitation_update: InvitationUpdateRequest, background_tasks: BackgroundTasks) -> ResponseSchema[InvitationResponse]:
        """Cập nhật trạng thái của một lời mời cụ thể."""
        # Get invitation from database
        invitation = await self.invitation_repo.get_by_id(invitation_id)
        if not invitation:
            raise NotFoundError("Invitation not found.")
        
        # Check permission - only target user can accept/decline
        if requester_uid != invitation.get("target_uid"):
            raise AppException(status_code=403, message="Only target user can update invitation status.")
        
        if invitation.get("status") != InvitationStatus.PENDING.value:
            raise AppException(status_code=400, message="Only pending invitations can be updated.")
        
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
                    collaborator_uids=[requester_uid]
                )
            
            elif invitation.get("type") == InvitationType.CONVERSATION.value:
                await conversation_repo.add_members(
                    conversation_id=updated_invitation.get("ref_id"),
                    member_uids=[requester_uid],
                    roles=[ConversationRole.MEMBER.value]
                )
                conversation_data = await conversation_repo.get_by_id(updated_invitation.get("ref_id"))
                # Tạo tóm tắt hội thoại cho người dùng mới này
                summary = {
                    "id": conversation_data.get("id"),
                    "name": conversation_data.get("name"),
                    "unread_count": 0,
                    "updated_at": datetime.now(timezone.utc)
                }
                background_tasks.add_task(
                    self.conversation_repository.upsert_user_conversation_summary, 
                    requester_uid, updated_invitation.get("ref_id"), summary
                )
        
        elif invitation_update.status == InvitationStatus.DECLINED:
            pass

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