from repositories.base_repo import BaseRepository

class TripRepository(BaseRepository):
    def __init__(self):
        super().__init__("trips")

    async def create(self, trip_data: dict) -> dict:
        """Tạo một trip mới."""
        return {}
    
    async def get_by_id(self, trip_id: str) -> dict:
        """Lấy thông tin một trip theo ID."""
        return {}
    
    async def update(self, trip_id: str, update_data: dict) -> dict:
        """Cập nhật thông tin một trip."""
        return {}
    
    async def add_members(self, trip_id: str, member_uids: list[str]) -> dict:
        """Thêm thành viên vào một trip."""
        return {}
    
    async def remove_members(self, trip_id: str, member_uids: list[str]) -> dict:
        """Xóa thành viên khỏi một trip."""
        return {}

    async def delete(self, trip_id: str) -> bool:
        """Xóa một trip."""
        return True
    
trip_repo = TripRepository()