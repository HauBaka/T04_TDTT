from __future__ import annotations

from repositories.user_repo import user_repo
from schemas.response_schema import ResponseSchema
from schemas.user_preference_schema import (
    UserTravelPreferenceResponse,
    UserTravelPreference,
    UserTravelPreferenceUpdateRequest,
)


class UserTravelPreferenceService:
    """Service xử lý nghiệp vụ liên quan UserTravelPreference."""

    def __init__(self):
        self.repo = user_repo

    async def update_my_travel_preference(
        self,
        uid: str,
        preference: UserTravelPreferenceUpdateRequest,
    ) -> ResponseSchema:
        """TODO: Tạo mới/cập nhật travel preference cho user hiện tại."""
        raise NotImplementedError()

    async def delete_my_travel_preference(
        self,
        uid: str,
    ) -> ResponseSchema[bool]:
        """TODO: Xóa travel preference của user hiện tại."""
        raise NotImplementedError()


user_travel_preference_service = UserTravelPreferenceService()
