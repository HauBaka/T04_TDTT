from fastapi import BackgroundTasks
from datetime import datetime, timedelta, timezone
from core.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from repositories.invitation_repo import invitation_repo
from repositories.user_repo import user_repo
from schemas.invitation_schema import InvitationCreateRequest, InvitationDocument, InvitationResponse, InvitationStatus, InvitationType, InvitationUpdateRequest
from schemas.notification_schema import NotificationCreateRequest, NotificationType
from schemas.response_schema import ResponseSchema
from services.notification_service import notification_service
from services.collection_service import collection_service

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
                await collection_service.add_accepted_contributors(
                    collection_id=updated_invitation.ref_id,
                    contributor_uids=[requester_uid]
                )
            
            elif updated_invitation.type == InvitationType.CONVERSATION:
                from services.conversation_service import conversation_service
                await conversation_service.add_accepted_members(
                    conversation_id=updated_invitation.ref_id,
                    new_uids=[requester_uid],
                    background_tasks=BackgroundTasks()
                )

            elif updated_invitation.type == InvitationType.TRIP:
                from services.trip_service import trip_service
                await trip_service.add_accepted_members(
                    trip_id=updated_invitation.ref_id,
                    member_uids=[requester_uid]
                )

        elif invitation_update.status == InvitationStatus.DECLINED:
            pass

        return self.build_invitation_response(updated_invitation)
    
    async def send_batch_invitations(self, sender_uid: str, target_uids: list[str], invitation_type: InvitationType, ref_id: str, invitation_content: str) -> list[InvitationResponse]:
        """Gửi hàng loạt lời mời."""
        batch = self.invitation_repo._db.batch()
        timestamp = datetime.now(timezone.utc)
        invitations = []

        for target_uid in target_uids:
            invitation_ref = self.invitation_repo._collection.document()
            invitation_doc = InvitationDocument(
                id=invitation_ref.id,
                sender_uid=sender_uid,
                target_uid=target_uid,
                type=invitation_type,
                ref_id=ref_id,
                status=InvitationStatus.PENDING,
                created_at=timestamp,
                updated_at=timestamp,
                expired_at=timestamp + timedelta(days=7),
            )
            batch.create(invitation_ref, invitation_doc.model_dump(mode="python", exclude_none=False))
            invitations.append(invitation_doc)

        await batch.commit()

        notifications = [
            NotificationCreateRequest(
                receiver_id=inv.target_uid,
                type=NotificationType.INVITATION,
                content=invitation_content,
                ref_id=inv.id,
                actor_id=inv.sender_uid
            )
            for inv in invitations
        ]

        await notification_service.create_batch_notifications(notifications)
        return invitations
    
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