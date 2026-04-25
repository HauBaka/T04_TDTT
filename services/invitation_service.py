from datetime import datetime

from repositories.invitation_repo import invitation_repo
from schemas.invitation_schema import InvitationCreateRequest, InvitationResponse, InvitationStatus, InvitationType, InvitationUpdateRequest
from schemas.response_schema import ResponseSchema
class InvitationService:
    def __init__(self):
        self.invitation_repo = invitation_repo

    async def create_invitation(self, sender_uid: str, invitation_request: InvitationCreateRequest) -> ResponseSchema[InvitationResponse]:
        """Tạo một lời mời mới."""
        return ResponseSchema[InvitationResponse](
            status_code=201,
            message="Invitation created successfully",
            data=InvitationResponse(
                id="invitation_id",
                sender_uid=sender_uid,
                target_uid=invitation_request.target_uid,
                type=invitation_request.type,
                ref_id=invitation_request.ref_id,
                status=InvitationStatus.PENDING,
                created_at=invitation_request.expired_at,
                expired_at=invitation_request.expired_at
            )
        )

    async def get_invitation(self, invitation_id: str, requester_uid: str) -> ResponseSchema[InvitationResponse]:
        """Lấy thông tin của một lời mời cụ thể."""
        return ResponseSchema[InvitationResponse](
            status_code=200,
            message="Invitation retrieved successfully",
            data=InvitationResponse(
                id=invitation_id,
                sender_uid="sender_uid",
                target_uid=requester_uid,
                type=InvitationType.CONVERSATION,
                ref_id="ref_id",
                status=InvitationStatus.PENDING,
                created_at=datetime.now(),
                expired_at=datetime.now()
            )
        )

    async def update_invitation(self, invitation_id: str, requester_uid: str, invitation_update: InvitationUpdateRequest) -> ResponseSchema[InvitationResponse]:
        """Cập nhật trạng thái của một lời mời cụ thể."""
        return ResponseSchema[InvitationResponse](
            status_code=200,
            message="Invitation updated successfully",
            data=InvitationResponse(
                id=invitation_id,
                sender_uid="sender_uid",
                target_uid=requester_uid,
                type=InvitationType.CONVERSATION,
                ref_id="ref_id",
                status=invitation_update.status,
                created_at=datetime.now(),
                expired_at=datetime.now()
        ))
    
    async def delete_invitation(self, invitation_id: str, requester_uid: str) -> bool:
        """Xóa một lời mời cụ thể."""
        return True
    
invitation_service = InvitationService()