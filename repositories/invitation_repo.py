from repositories.base_repo import BaseRepository

class InvitationRepository(BaseRepository):
    def __init__(self):
        super().__init__("invitations")

    async def create(self, invitation_data: dict) -> dict:
        """Tạo một lời mời mới."""
        return {}
    
    async def get_by_id(self, invitation_id: str) -> dict:
        """Lấy thông tin một lời mời theo ID."""
        return {}
    
    async def update(self, invitation_id: str, update_data: dict) -> dict:
        """Cập nhật thông tin một lời mời."""
        return {}

    async def delete(self, invitation_id: str) -> bool:
        """Xóa một lời mời."""
        return True
    
invitation_repo = InvitationRepository()