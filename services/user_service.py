from core.exceptions import ConflictError, NotFoundError
from repositories.user_repo import user_repo
from repositories.collection_repo import collection_repo
from schemas.user_schema import UserPublic, UserPrivate
from schemas.user_preference_schema import UserTravelPreferenceResponse, UserTravelPreference, UserTravelPreferenceUpdateRequest
from schemas.response_schema import ResponseSchema

ALLOWED_UPDATE_FIELDS = {"display_name", "username", "email", "phone_number", "bio", "avatar_url"}

class UserService:
    def __init__(self):
        self.user_repo = user_repo

    async def get_me(self, requester_uid: str) -> ResponseSchema:
        user_dict = await self.user_repo.get_user(requester_uid)

        if not user_dict:
            raise NotFoundError("User not found")

        return ResponseSchema(status_code=200, message="Profile retrieved successfully", data=UserPrivate(**user_dict))
        
    async def get_profile(self, requester_uid: str | None, target_username: str) -> ResponseSchema:
        target_user_dict = await self.user_repo.get_user_by_username(target_username)
        if not target_user_dict:
            raise NotFoundError("User not found")
 
        is_owner = requester_uid == target_user_dict.get("uid")
        user_data = UserPrivate(**target_user_dict) if is_owner else UserPublic(**target_user_dict)
 
        return ResponseSchema(status_code=200, message="Profile retrieved successfully", data=user_data)    
        
    async def update_profile(self, requester_uid: str, update_data: dict) -> ResponseSchema:
        #lọc bỏ các field None để không ghi đè dữ liệu cũ
        filtered_data = {
            k: v for k, v in update_data.items()
            if v is not None and k in ALLOWED_UPDATE_FIELDS
        }
        # Check trùng username
        if "username" in filtered_data:
            existing = await self.user_repo.get_user_by_username(filtered_data["username"])
            if existing and existing.get("uid") != requester_uid:
                raise ConflictError("Username already taken")
            
            filtered_data["username_lower"] = filtered_data["username"].lower()

        # Check trùng email
        if "email" in filtered_data:
            filtered_data["email"] = filtered_data["email"].lower()
            existing = await self.user_repo.get_user_by_email(filtered_data["email"])
            if existing and existing.get("uid") != requester_uid:
                raise ConflictError("Email already in use")
                
        if filtered_data:
            await self.user_repo.update_user(requester_uid, filtered_data)
            
        updated_user_dict = await self.user_repo.get_user(requester_uid)
        if not updated_user_dict:
            raise NotFoundError("User not found after update")
        
        return ResponseSchema(status_code=200, message="Profile updated successfully", data=UserPrivate(**updated_user_dict))
        
    async def update_liked_collection(self, requester_uid: str, place_id: str, add: bool) -> ResponseSchema:
        return ResponseSchema(status_code=200, message="Liked collection updated successfully", data=None)

    async def delete_profile(self, requester_uid: str) -> ResponseSchema:
        deleted = await self.user_repo.delete_user(requester_uid)
        if not deleted:
            raise NotFoundError("User not found")
        
        return ResponseSchema(status_code=200, message="Account deleted successfully", data=None)
        
    async def get_collections(self, requester_uid: str) -> ResponseSchema:
        owned_collections = await collection_repo.get_user_collections(requester_uid)
        collaborated_collections = await collection_repo.get_collaborated_collections(requester_uid)
        
        return ResponseSchema(status_code=200, message="Collections retrieved successfully", data={
            "owned": owned_collections,
            "collaborated": collaborated_collections
        })

    async def get_travel_preference(self, uid: str) -> ResponseSchema[UserTravelPreferenceResponse]:
        """Lấy travel preference của user."""
        preference_dict = await self.user_repo.get_travel_preference(uid)
        if not preference_dict:
            raise NotFoundError("Travel profile not found")
        
        preference_data = UserTravelPreference(**preference_dict)
        return ResponseSchema(
            status_code=200,
            message="Travel preference retrieved successfully",
            data=UserTravelPreferenceResponse(preference=preference_data)
        )

    async def update_travel_preference(
        self,
        uid: str,
        preference: UserTravelPreferenceUpdateRequest,
    ) -> ResponseSchema[UserTravelPreferenceResponse]:
        """Tạo mới/cập nhật travel preference cho user."""
        # Chuyển đổi thành dict, loại bỏ các trường None (exclude_unset=True)
        preference_data = preference.model_dump(exclude_unset=True)
        
        # Nếu có preference cũ, merge với cái mới
        existing_preference_dict = await self.user_repo.get_travel_preference(uid) or {}
        if existing_preference_dict:
            existing_preference_dict.update(preference_data)
            preference_data = existing_preference_dict
        
        # Ghi vào database
        updated_data = await self.user_repo.update_travel_preference(uid, preference_data)
        
        # Tạo response
        preference_model = UserTravelPreference(**updated_data)
        return ResponseSchema(
            status_code=200,
            message="Travel preference updated successfully",
            data=UserTravelPreferenceResponse(preference=preference_model)
        )

    async def delete_travel_preference(self, uid: str) -> ResponseSchema[bool]:
        """Xóa travel preference của user."""
        deleted = await self.user_repo.delete_travel_preference(uid)
        if not deleted:
            raise NotFoundError("User not found or preference could not be deleted")
        
        return ResponseSchema(
            status_code=200,
            message="Travel preference deleted successfully",
            data=deleted
        )

user_service = UserService()
