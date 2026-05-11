from __future__ import annotations

from repositories.user_travel_preference_repo import user_travel_preference_repo
from schemas.response_schema import ResponseSchema
from schemas.user_preference_schema import (
    UserTravelPreferenceResponse,
    UserTravelPreference,
    UserTravelPreferenceUpsertRequest,
)


class UserTravelPreferenceService:
    """Service xử lý nghiệp vụ liên quan UserTravelPreference."""

    def __init__(self):
        self.repo = user_travel_preference_repo

    async def upsert_my_travel_preference(
        self,
        uid: str,
        preference: UserTravelPreferenceUpsertRequest,
    ) -> ResponseSchema:
        """TODO: Tạo mới/cập nhật travel preference cho user hiện tại."""
        raise NotImplementedError()

    async def get_my_travel_preference(
        self,
        uid: str,
    ) -> ResponseSchema[UserTravelPreferenceResponse]:
        """TODO: Lấy travel preference của user hiện tại."""
        raise NotImplementedError()

    async def delete_my_travel_preference(
        self,
        uid: str,
    ) -> ResponseSchema[bool]:
        """TODO: Xóa travel preference của user hiện tại."""
        raise NotImplementedError()


user_travel_preference_service = UserTravelPreferenceService()
