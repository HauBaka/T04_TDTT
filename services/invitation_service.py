from fastapi import BackgroundTasks
from datetime import datetime, timezone
from core.exceptions import BadRequestError, NotFoundError, AppException, PermissionDeniedError
from repositories.invitation_repo import invitation_repo
from repositories.user_repo import user_repo
from schemas.conversation_schema import ConversationRole, UserConversationSummaryUpdate
from schemas.invitation_schema import InvitationCreateRequest, InvitationDocument, InvitationResponse, InvitationStatus, InvitationType, InvitationUpdateRequest
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
        
        invitation = await self.invitation_repo.create(sender_uid, invitation_request)
        return self.build_invitation_response(invitation)

    async def update_invitation(self, invitation_id: str, requester_uid: str, invitation_update: InvitationUpdateRequest) -> ResponseSchema[InvitationResponse]:
        """Cập nhật trạng thái của một lời mời cụ thể."""
        # Get invitation from database
        invitation = await self.invitation_repo.get_by_id(invitation_id)
        
        # Check permission - only target user can accept/decline
        if requester_uid != invitation.target_uid:
            raise PermissionDeniedError("You do not have permission to update this invitation.")
        
        if invitation.status != InvitationStatus.PENDING:
            raise BadRequestError("Only pending invitations can be updated.")
        
        updated_invitation = await self.invitation_repo.update(invitation_id, invitation_update)

        if invitation_update.status == InvitationStatus.ACCEPTED:
            if updated_invitation.type == InvitationType.COLLECTION:
                await collection_repo.add_contributors_to_collection(
                    collection_id=updated_invitation.ref_id,
                    contributor_uids=[requester_uid]
                )
            
            elif updated_invitation.type == InvitationType.CONVERSATION:
                updated_conversation =await conversation_repo.add_members(
                    conversation_id=updated_invitation.ref_id,
                    member_uids=[requester_uid],
                    roles=[ConversationRole.MEMBER.value]
                )
                # Tạo tóm tắt hội thoại cho người dùng mới này
                summary = UserConversationSummaryUpdate(
                    name=updated_conversation.name,
                    description=updated_conversation.description,
                    thumbnail_url=updated_conversation.thumbnail_url,
                    unread_count = 0,
                    latest_msg=None
                )
                await conversation_repo.upsert_user_conversation_summary(
                    requester_uid, updated_invitation.ref_id, summary
                )

        elif invitation_update.status == InvitationStatus.DECLINED:
            pass

        return self.build_invitation_response(updated_invitation)
    
    async def delete_invitation(self, invitation_id: str, requester_uid: str) -> ResponseSchema[bool]:
        """Xóa một lời mời cụ thể."""
        # Get invitation from database
        invitation = await self.invitation_repo.get_by_id(invitation_id)
        
        # Check permission - only sender or target can delete
        if invitation.sender_uid != requester_uid and invitation.target_uid != requester_uid:
            raise PermissionDeniedError("You do not have permission to delete this invitation.")
        
        # Delete from database
        await self.invitation_repo.delete(invitation_id)
        return ResponseSchema[bool](data=True)
    
    def build_invitation_response(self, invitation_data: InvitationDocument) -> ResponseSchema[InvitationResponse]:
        """Xây dựng response từ invitation data."""
        
        invitation = InvitationResponse(
            id = invitation_data.id,
            sender_uid = invitation_data.sender_uid,
            target_uid = invitation_data.target_uid,
            type = invitation_data.type,
            ref_id = invitation_data.ref_id,
            status = invitation_data.status,
            created_at = invitation_data.created_at,
            expired_at = invitation_data.expired_at
        )
        return ResponseSchema[InvitationResponse](data=invitation)

invitation_service = InvitationService()