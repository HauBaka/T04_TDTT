from fastapi import BackgroundTasks
from datetime import datetime, timedelta, timezone
from core.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from repositories.invitation_repo import invitation_repo
from repositories.user_repo import user_repo
from schemas.invitation_schema import GetPendingInvitationsRequest, InvitationCreateRequest, InvitationDocument, InvitationResponse, InvitationStatus, InvitationType, InvitationUpdateRequest
from schemas.notification_schema import NotificationCreateRequest, NotificationType
from schemas.response_schema import ResponseSchema
from services.notification_service import notification_service
from services.collection_service import collection_service

class InvitationService:
    def __init__(self):
        self.invitation_repo = invitation_repo

    async def get_invitation(self, invitation_id: str, requester_uid: str) -> ResponseSchema[InvitationResponse]:
        """Lấy thông tin của một lời mời cụ thể."""
        invitation = await self.invitation_repo.get_by_id(invitation_id)
        
        # Check permission - only sender or target can view
        if invitation.sender_uid != requester_uid and invitation.target_uid != requester_uid:
            raise PermissionDeniedError("You do not have permission to view this invitation.")
        
        return self.build_invitation_response(invitation)

    async def update_invitation(self, invitation_id: str, requester_uid: str, invitation_update: InvitationUpdateRequest, background_tasks: BackgroundTasks) -> ResponseSchema[InvitationResponse]:
        """Cập nhật trạng thái của một lời mời cụ thể."""
        # Get invitation from database
        invitation = await self.invitation_repo.get_by_id(invitation_id)
        
        # Check permission - only target user can accept/decline
        if requester_uid != invitation.target_uid:
            raise PermissionDeniedError("You do not have permission to update this invitation.")
        
        if invitation.status != InvitationStatus.PENDING:
            raise BadRequestError("Only pending invitations can be updated.")
        
        if invitation.expired_at < self.invitation_repo._current_timestamp:
            if invitation.status != InvitationStatus.EXPIRED:
                await self.invitation_repo.update(invitation_id, InvitationUpdateRequest(status=InvitationStatus.EXPIRED))
            raise BadRequestError("This invitation has expired.")
        
        if invitation_update.status == InvitationStatus.ACCEPTED:
            if invitation.type == InvitationType.COLLECTION:
                await collection_service.add_accepted_contributor(
                    collection_id=invitation.ref_id,
                    contributor_uid=requester_uid
                )
            elif invitation.type == InvitationType.CONVERSATION:
                from services.conversation_service import conversation_service
                await conversation_service.add_accepted_member(
                    conversation_id=invitation.ref_id,
                    new_uid=requester_uid,
                    background_tasks=background_tasks
                )
            elif invitation.type == InvitationType.TRIP:
                from services.trip_service import trip_service
                await trip_service.add_accepted_member(
                    trip_id=invitation.ref_id,
                    member_uid=requester_uid
                )

        updated_invitation = await self.invitation_repo.update(invitation_id, invitation_update)


        target = await user_repo.get_user(invitation.target_uid)
        target_name = target.display_name if target else "Unknown User"
        sender_notification_content = f"{target_name} {updated_invitation.status.display_name.lower()} lời mời tham gia vào {invitation.type.display_name} (ID: {invitation.ref_id}) của bạn."

        await notification_service.create_notification(
            NotificationCreateRequest(
                receiver_id=invitation.sender_uid,
                type=NotificationType.INVITATION,
                content=sender_notification_content,
                ref_id=invitation.id,
                actor_id=invitation.target_uid
            )
        )

        return self.build_invitation_response(updated_invitation)
    
    async def send_batch_invitations(self, invitation_requests: list[InvitationCreateRequest]) -> list[InvitationResponse]:
        """Gửi hàng loạt lời mời."""
        # Lọc những invitation vẫn còn hiệu lực để tránh gửi trùng lặp
        pending_invitations = await self.invitation_repo.get_pending_invitations_for_user([
            GetPendingInvitationsRequest(
                target_uid=req.target_uid,
                actor_uid=req.sender_uid,
                type=req.type,
                ref_id=req.ref_id
            ) for req in invitation_requests
        ])

        senders = await user_repo.get_users(list(set(req.sender_uid for req in invitation_requests)))
        
        # Lọc danh sách request cần tạo
        requests_to_create = [
            req for req in invitation_requests
            if f"{req.target_uid}_{req.sender_uid}_{req.type.value}_{req.ref_id}" not in pending_invitations
        ]

        # Tạo batch cho những request chưa tồn tại
        new_invitations = []
        if requests_to_create:
            new_invitations = await self.invitation_repo.create_batch(invitation_requests=requests_to_create)

        # Gửi thông báo cho những lời mời 
        notifications = []
        for inv in new_invitations:
            sender_name = "Unknown User"
            if senders.get(inv.sender_uid):
                sender_name = senders[inv.sender_uid].display_name or sender_name

            notification_req = NotificationCreateRequest(
                receiver_id=inv.target_uid,
                type=NotificationType.INVITATION,
                content=f"{sender_name} {inv.type.invitation_label} (ID: {inv.ref_id}).",
                ref_id=inv.id,
                actor_id=inv.sender_uid
            )
            notifications.append(notification_req)

        if notifications:
            await notification_service.create_batch_notifications(notifications)

        # Gộp cả cũ và mới đầy đủ kết quả cho Client như cũ
        all_invitations = list(pending_invitations.values()) + new_invitations

        def to_response(invitation: InvitationDocument) -> InvitationResponse:
            return InvitationResponse(
                id=invitation.id,
                sender_uid=invitation.sender_uid,
                target_uid=invitation.target_uid,
                type=invitation.type,
                ref_id=invitation.ref_id,
                status=invitation.status,
                created_at=invitation.created_at,
                expired_at=invitation.expired_at
            )

        return [to_response(inv) for inv in all_invitations]
    
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