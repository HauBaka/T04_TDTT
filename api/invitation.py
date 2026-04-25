from fastapi import APIRouter, Depends
from schemas.response_schema import ResponseSchema
from core.dependencies import get_current_user
from services.invitation_service import invitation_service
from schemas.invitation_schema import InvitationCreateRequest, InvitationResponse, InvitationUpdateRequest

invitation_router = APIRouter()

@invitation_router.post("/invitations", response_model=ResponseSchema[InvitationResponse])
async def create_invitation(invitation_request: InvitationCreateRequest, requester=Depends(get_current_user(optional=False))):
    """Tạo một lời mời mới cho người dùng đã xác thực."""
    return await invitation_service.create_invitation(requester.get("uid"), invitation_request)

@invitation_router.get("/invitations/{invitation_id}", response_model=ResponseSchema[InvitationResponse])
async def get_invitation(invitation_id: str, requester=Depends(get_current_user(optional=False))):
    """Lấy thông tin của một lời mời cụ thể."""
    return await invitation_service.get_invitation(invitation_id, requester.get("uid"))

@invitation_router.patch("/invitations/{invitation_id}", response_model=ResponseSchema[InvitationResponse])
async def update_invitation(invitation_id: str, invitation_request: InvitationUpdateRequest, requester=Depends(get_current_user(optional=False))):
    """Cập nhật trạng thái của một lời mời cụ thể."""
    return await invitation_service.update_invitation(invitation_id, requester.get("uid"), invitation_request)

@invitation_router.delete("/invitations/{invitation_id}", response_model=ResponseSchema[bool])
async def delete_invitation(invitation_id: str, requester=Depends(get_current_user(optional=False))):
    """Xóa một lời mời cụ thể."""
    return await invitation_service.delete_invitation(invitation_id, requester.get("uid"))

