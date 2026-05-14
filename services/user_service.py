import asyncio

from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from repositories.collection_repo import collection_repo
from repositories.conversation_repo import conversation_repo
from repositories.user_repo import user_repo
from schemas.collection_schema import (
    CollectionPlaceResponse,
    CollectionPrivateResponse,
    CollectionPublicResponse,
)
from schemas.conversation_schema import ConversationResponse
from schemas.response_schema import ResponseSchema
from schemas.user_schema import (
    UserPrivateResponse,
    UserPublicResponse,
    UserSaveCollectionRequest,
    UserUpdateRequest,
)
from schemas.view_schema import ViewResponse
from services.collection_service import collection_service

ALLOWED_UPDATE_FIELDS = {
    "display_name",
    "username",
    "email",
    "phone_number",
    "bio",
    "avatar_url",
}


class UserService:
    def __init__(self):
        self.user_repo = user_repo

    async def get_me(self, requester_uid: str) -> ResponseSchema[UserPrivateResponse]:
        user_doc = await self.user_repo.get_user(requester_uid)

        try:
            return ResponseSchema(
                status_code=200,
                message="Profile retrieved successfully",
                data=UserPrivateResponse.model_validate(user_doc),
            )

        except PydanticValidationError as e:
            logger.error(f"Error validating user data for uid {requester_uid}: {e}")
            raise ValidationError("Failed to validate user data!")

    async def get_profile(
        self, requester_uid: str | None, target_username: str
    ) -> ResponseSchema[UserPublicResponse | UserPrivateResponse]:
        target_user = await self.user_repo.get_user_by_username(target_username)

        is_owner = requester_uid == target_user.uid
        user_data = (
            UserPrivateResponse.model_validate(target_user)
            if is_owner
            else UserPublicResponse.model_validate(target_user)
        )

        return ResponseSchema(
            status_code=200, message="Profile retrieved successfully", data=user_data
        )

    async def update_profile(
        self, requester_uid: str, update_data: UserUpdateRequest
    ) -> ResponseSchema[UserPrivateResponse]:
        # lọc bỏ các field None để không ghi đè dữ liệu cũ
        payload = update_data.model_dump(exclude_none=True)
        filtered_data = {k: v for k, v in payload.items() if k in ALLOWED_UPDATE_FIELDS}
        # Check trùng username
        if "username" in filtered_data:
            try:
                existing = await self.user_repo.get_user_by_username(
                    filtered_data["username"]
                )
            except NotFoundError:
                existing = None

            if existing and existing.uid != requester_uid:
                raise ConflictError("Username already taken")

            filtered_data["username_lower"] = filtered_data["username"].lower()

        # Check trùng email
        if "email" in filtered_data:
            filtered_data["email"] = filtered_data["email"].lower()
            try:
                existing = await self.user_repo.get_user_by_email(
                    filtered_data["email"]
                )
            except NotFoundError:
                existing = None

            if existing and existing.uid != requester_uid:
                raise ConflictError("Email already in use")

        if filtered_data:
            await self.user_repo.batch_update_users([requester_uid], [filtered_data])

        updated_user_dict = await self.user_repo.get_user(requester_uid)

        return ResponseSchema(
            status_code=200,
            message="Profile updated successfully",
            data=UserPrivateResponse.model_validate(updated_user_dict),
        )

    async def delete_profile(self, requester_uid: str) -> ResponseSchema:
        deleted = await self.user_repo.delete_user(requester_uid)

        return ResponseSchema(
            status_code=200, message="Account deleted successfully", data=deleted
        )

    async def get_owned_collections(
        self, requester_uid: str
    ) -> ResponseSchema[list[CollectionPrivateResponse]]:
        user_doc = await self.user_repo.get_user(requester_uid)
        owned_collections = (
            await collection_repo.get_user_collections(user_doc.uid) or []
        )
        # Loại default liked collection
        return_collections = [
            col for col in owned_collections if col.id != user_doc.liked_collection
        ]

        def to_private(doc) -> CollectionPrivateResponse:
            return CollectionPrivateResponse(
                id=doc.id,
                owner_uid=doc.owner_uid,
                name=doc.name,
                description=doc.description,
                thumbnail_url=doc.thumbnail_url,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                saved_count=doc.saved_count,
                contributor_count=doc.contributor_count,
                place_count=doc.place_count,
                views=doc.views or ViewResponse(),
                tags=doc.tags,
                visibility=doc.visibility,
            )

        return ResponseSchema(
            status_code=200,
            message="Collections retrieved successfully",
            data=[to_private(doc) for doc in return_collections],
        )

    async def get_contributing_collections(
        self, requester_uid: str
    ) -> ResponseSchema[list[CollectionPrivateResponse]]:
        contributing_collections = (
            await collection_repo.get_contributed_collections(requester_uid) or []
        )

        def to_private(doc) -> CollectionPrivateResponse:
            return CollectionPrivateResponse(
                id=doc.id,
                owner_uid=doc.owner_uid,
                name=doc.name,
                description=doc.description,
                thumbnail_url=doc.thumbnail_url,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                saved_count=doc.saved_count,
                contributor_count=doc.contributor_count,
                place_count=doc.place_count,
                views=doc.views or ViewResponse(),
                tags=doc.tags,
                visibility=doc.visibility,
            )

        return ResponseSchema(
            status_code=200,
            message="Collections retrieved successfully",
            data=[to_private(doc) for doc in contributing_collections],
        )

    async def get_saved_collections(
        self, requester_uid: str
    ) -> ResponseSchema[list[CollectionPublicResponse]]:
        saved_collections = (
            await collection_repo.get_saved_collections(requester_uid) or []
        )

        def to_public(doc) -> CollectionPublicResponse:
            return CollectionPublicResponse(
                id=doc.id,
                owner_uid=doc.owner_uid,
                name=doc.name,
                description=doc.description,
                thumbnail_url=doc.thumbnail_url,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                saved_count=doc.saved_count,
                contributor_count=doc.contributor_count,
                place_count=doc.place_count,
                views=doc.views or ViewResponse(),
                tags=doc.tags,
                visibility=doc.visibility,
            )

        return ResponseSchema(
            status_code=200,
            message="Collections retrieved successfully",
            data=[to_public(doc) for doc in saved_collections],
        )

    async def save_collection(
        self, requester_uid: str, collection: UserSaveCollectionRequest
    ) -> ResponseSchema[bool]:
        # Check collection exists
        collection_doc = await collection_repo.get_collection(collection.collection_id)
        user_doc = await self.user_repo.get_user(requester_uid)
        # Check already saved
        if collection_doc.id in user_doc.saved_collections:
            raise BadRequestError("Collection already saved")

        # Check default liked collection - không cho lưu vì collection này dùng để lưu danh sách địa điểm yêu thích của user, không phải collection thực sự
        if collection_doc.id == user_doc.liked_collection:
            raise BadRequestError("Cannot perform this action")

        # Save collection
        await asyncio.gather(
            self.user_repo.save_collection(requester_uid, collection.collection_id),
            collection_repo.add_saver(collection.collection_id, requester_uid),
        )

        return ResponseSchema(
            status_code=200, message="Collection saved successfully", data=True
        )

    async def unsave_collection(
        self, requester_uid: str, collection_id: str
    ) -> ResponseSchema[bool]:
        # Check collection exists
        collection_doc = await collection_repo.get_collection(collection_id)
        user_doc = await self.user_repo.get_user(requester_uid)
        # Check already saved
        if collection_doc.id not in user_doc.saved_collections:
            raise BadRequestError("Collection not in saved list")

        # Unsave collection
        await asyncio.gather(
            self.user_repo.unsave_collection(requester_uid, collection_id),
            collection_repo.remove_saver(collection_id, requester_uid),
        )

        return ResponseSchema(
            status_code=200, message="Collection unsaved successfully", data=True
        )

    async def add_favourite_place(
        self, requester_uid: str, place_id: str
    ) -> ResponseSchema[bool]:
        user_doc = await self.user_repo.get_user(requester_uid)

        try:
            await collection_service.add_places_to_collection(
                user_doc.liked_collection, requester_uid, [place_id]
            )
            return ResponseSchema(
                status_code=200,
                message="Place added to favourite successfully",
                data=True,
            )
        except Exception as e:
            return ResponseSchema(
                status_code=500,
                message=f"Failed to add place to favourite: {str(e)}",
                data=False,
            )

    async def remove_favourite_place(
        self, requester_uid: str, place_id: str
    ) -> ResponseSchema[bool]:
        user_doc = await self.user_repo.get_user(requester_uid)

        try:
            await collection_service.remove_places_from_collection(
                user_doc.liked_collection, requester_uid, [place_id]
            )
            return ResponseSchema(
                status_code=200,
                message="Place removed from favourite successfully",
                data=True,
            )
        except Exception as e:
            return ResponseSchema(
                status_code=500,
                message=f"Failed to remove place from favourite: {str(e)}",
                data=False,
            )

    async def get_favourite_places(
        self, requester_uid: str
    ) -> ResponseSchema[list[CollectionPlaceResponse]]:
        try:
            user_doc = await self.user_repo.get_user(requester_uid)
            favourite_place_collection = (
                await collection_repo.get_places_from_collection(
                    user_doc.liked_collection
                )
            )

            return ResponseSchema(
                status_code=200,
                message="Favourite places retrieved successfully",
                data=favourite_place_collection,
            )
        except Exception as e:
            logger.error(
                f"Error retrieving favourite places for user {requester_uid}: {str(e)}"
            )
            return ResponseSchema(
                status_code=500,
                message="Failed to retrieve favourite places!",
                data=[],
            )

    async def get_conversations(
        self, requester_uid: str
    ) -> ResponseSchema[list[ConversationResponse]]:
        user = await self.user_repo.get_user(requester_uid)

        conversation_docs = (
            await conversation_repo.get_by_ids(
                [conv_id for conv_id in user.conversations]
            )
            if user.conversations
            else []
        )

        conversations = []

        for doc in conversation_docs:
            conv = ConversationResponse(
                id=doc.id,
                owner_uid=doc.owner_uid,
                name=doc.name,
                description=doc.description,
                thumbnail_url=doc.thumbnail_url,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                member_count=len(doc.member_uids),
            )
            conversations.append(conv)

        return ResponseSchema(
            status_code=200,
            message="Conversations retrieved successfully",
            data=conversations,
        )


user_service = UserService()
