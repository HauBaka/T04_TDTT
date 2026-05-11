from __future__ import annotations

from repositories.base_repo import BaseRepository
from schemas.user_preference_schema import UserTravelPreference


class UserTravelPreferenceRepository(BaseRepository):
    """Repository quản lý dữ liệu UserTravelPreference của người dùng."""

    def __init__(self):
        super().__init__("users")

    async def get_user_travel_preference(self, uid: str) -> UserTravelPreference | None:
        """TODO: Lấy travel preference của một người dùng theo uid."""
        raise NotImplementedError()

    async def upsert_user_travel_preference(
        self,
        uid: str,
        preference: UserTravelPreference,
    ) -> UserTravelPreference:
        """TODO: Tạo mới/cập nhật travel preference của người dùng."""
        raise NotImplementedError()

    async def delete_user_travel_preference(self, uid: str) -> bool:
        """TODO: Xóa travel preference của một người dùng."""
        raise NotImplementedError()


user_travel_preference_repo = UserTravelPreferenceRepository()
