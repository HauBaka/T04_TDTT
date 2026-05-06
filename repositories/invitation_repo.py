from repositories.base_repo import BaseRepository

class InvitationRepository(BaseRepository):
    def __init__(self):
        super().__init__("invitations")

    async def create(self, invitation_data: dict) -> dict:
        """Tạo một lời mời mới."""
        invitation_id = await self._create(invitation_data)
        invitation_data["id"] = invitation_id
        return invitation_data
    
    async def get_by_id(self, invitation_id: str) -> dict:
        """Lấy thông tin một lời mời theo ID."""
        return await self._get_by_id(invitation_id)
    
    async def update(self, invitation_id: str, update_data: dict) -> dict:
        """Cập nhật thông tin một lời mời."""
        await self._update(invitation_id, update_data)
        return await self._get_by_id(invitation_id)

    async def delete(self, invitation_id: str) -> bool:
        """Xóa một lời mời."""
        return await self._delete(invitation_id)
    
invitation_repo = InvitationRepository()