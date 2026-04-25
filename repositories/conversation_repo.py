from repositories.base_repo import BaseRepository

class ConversationRepository(BaseRepository):
    def __init__(self):
        super().__init__("conversations")


    async def create(self, conversation_data: dict) -> dict:
        """Tạo một conversation mới."""
        return {}
    
    async def get_by_id(self, conversation_id: str) -> dict:
        """Lấy thông tin một conversation theo ID."""
        return {}
    
    async def update(self, conversation_id: str, update_data: dict) -> dict:
        """Cập nhật thông tin một conversation."""
        return {}
    
    async def add_members(self, conversation_id: str, member_uids: list[str]) -> dict:
        """Thêm thành viên vào một conversation."""
        return {}
    
    async def remove_members(self, conversation_id: str, member_uids: list[str]) -> dict:
        """Xóa thành viên khỏi một conversation."""
        return {}
    
    async def send_message(self, conversation_id: str, message_data: dict) -> dict:
        """Gửi một tin nhắn mới vào một conversation."""
        return {}
    
    async def delete_message(self, conversation_id: str, message_id: str) -> dict:
        """Xóa một tin nhắn khỏi một conversation."""
        return {}

    async def delete(self, conversation_id: str) -> bool:
        """Xóa một conversation."""
        return True

conversation_repo = ConversationRepository()