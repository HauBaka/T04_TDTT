import asyncio

from google.cloud import firestore as fs
from google.cloud.firestore_v1.base_query import FieldFilter
from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import (
    BadRequestError,
    DatabaseError,
    NotFoundError,
    ValidationError,
)
from repositories.base_repo import BaseRepository
from schemas.user_schema import SavedCollectionDocument, UserCreateRequest, UserDocument


class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__("users")

    async def get_user(self, uid: str) -> UserDocument:
        """Lấy thông tin user theo uid

        Raises:
            NotFoundError: Nếu user không tồn tại hoặc data rỗng
            ValidationError: Nếu lỗi trong quá trình validate dữ liệu
        """
        data = await self._get_by_id(uid)

        try:
            return UserDocument.model_validate(data)
        except PydanticValidationError as e:
            logger.error(f"Error validating user data for uid {uid}: {str(e)}")
            raise ValidationError("Failed to validate user data")

    async def create_user(self, user_request: UserCreateRequest) -> UserDocument:
        """Tạo user mới"""
        user_doc = UserDocument(
            uid=user_request.uid,
            username=user_request.username,
            username_lower=user_request.username_lower,
            email=user_request.email,
            display_name=user_request.display_name,
            avatar_url=user_request.avatar_url,
            bio=user_request.bio,
            liked_collection=user_request.liked_collection,
            chatbot_conversation=user_request.chatbot_conversation,
            phone_number=user_request.phone_number,
            created_at=user_request.created_at,
            last_login=user_request.last_login,
            last_updated=user_request.last_updated,
            travel_profile=None,
            scoring_weights=None,
        )
        await self._create(user_doc.model_dump(mode="python"), doc_id=user_doc.uid)

        return user_doc

    async def get_users(self, uids: list[str]) -> dict[str, UserDocument]:
        """
        Lấy thông tin của nhiều user cùng lúc.
        Trả về dict dạng map: { "uid_1": {user_data}, "uid_2": {user_data} }

        Raises:
            ValidationError: Nếu uids rỗng
        """
        if not uids:
            raise ValidationError("No user IDs provided")

        unique_uids = list(set(uids))
        result = {}
        chunk_size = 30

        tasks = []
        for i in range(0, len(unique_uids), chunk_size):
            chunk = unique_uids[i : i + chunk_size]
            query = self._collection.where(filter=FieldFilter("uid", "in", chunk)).get()
            tasks.append(query)

        results_list = await asyncio.gather(*tasks)
        for docs in results_list:
            for doc in docs:
                user_data = doc.to_dict()
                # Thêm if để pass qua khâu check lỗi của Pylance
                if user_data:
                    user_data["uid"] = doc.id
                    try:
                        result[doc.id] = UserDocument.model_validate(user_data)
                    except PydanticValidationError as e:
                        logger.error(
                            f"Error validating user data for uid {doc.id}: {str(e)}"
                        )

        return result

    async def delete_user(self, uid: str) -> bool:
        """Xóa user theo uid"""
        return await self._delete(uid)

    async def get_user_by_username(self, username: str) -> UserDocument:
        """Lấy user theo username (không phân biệt hoa thường)

        Raises:
            NotFoundError: Nếu user không tồn tại hoặc data rỗng
            ValidationError: Nếu lỗi trong quá trình validate dữ liệu
        """
        docs = (
            await self._collection.where(
                filter=FieldFilter("username_lower", "==", username.lower())
            )
            .limit(1)
            .get()
        )
        for doc in docs:
            try:
                return UserDocument.model_validate(doc.to_dict())
            except PydanticValidationError as e:
                logger.error(f"Error validating user data for uid {doc.id}: {str(e)}")
                raise ValidationError("Failed to validate user data for retrieval")
        raise NotFoundError("User not found")

    async def get_user_by_email(self, email: str) -> UserDocument:
        """Lấy user theo email (không phân biệt hoa thường)

        Raises:
            NotFoundError: Nếu user không tồn tại hoặc data rỗng
            ValidationError: Nếu lỗi trong quá trình validate dữ liệu
        """
        docs = (
            await self._collection.where(
                filter=FieldFilter("email", "==", email.lower())
            )
            .limit(1)
            .get()
        )

        for doc in docs:
            try:
                return UserDocument.model_validate(doc.to_dict())
            except PydanticValidationError as e:
                logger.error(f"Error validating user data for uid {doc.id}: {str(e)}")
                raise ValidationError("Failed to validate user data for retrieval")

        raise NotFoundError("User not found")

    async def batch_update_users(
        self, uids: list[str], update_data: list[dict]
    ) -> bool:
        """
        Cập nhật nhiều user cùng lúc.

        Raises:
            ValidationError: Nếu uids rỗng hoặc mismatch giữa số lượng uids và update_data, hoặc lỗi trong quá trình cập nhật
        """
        if not uids:
            raise ValidationError("No user IDs provided for update")

        if len(uids) != len(update_data):
            raise ValidationError("Mismatch between number of user IDs and update data")

        now = self._current_timestamp
        for data in update_data:
            data["last_updated"] = now
        # Firestore giới hạn 500 thao tác mỗi batch
        chunk_size = 500

        try:
            pairs = list(zip(uids, update_data))
            for i in range(0, len(pairs), chunk_size):
                chunk = pairs[i : i + chunk_size]
                batch = self._db.batch()

                for uid, data in chunk:
                    user_ref = self._collection.document(uid)
                    batch.update(user_ref, data)
                await batch.commit()

            return True
        except Exception as e:
            logger.error(f"Error in batch_update_users: {str(e)}")
            raise DatabaseError("Failed to update users")

    async def save_collection(self, requester_uid: str, collection_id: str) -> bool:
        """Lưu một collection vào danh sách đã lưu của user

        users/{uid}

            saved_collections: [collection_id_1, collection_id_2, ...]

            /saved_collections/{collection_id}
                collection_id: str
                saved_at: timestamp

        Raises:
            NotFoundError: Nếu user không tồn tại
            BadRequestError: Nếu collection đã được lưu trước đó
        """
        user_doc = await self.get_user(requester_uid)
        batch = self._db.batch()
        if collection_id in user_doc.saved_collections:
            raise BadRequestError("Collection already saved")

        # Thêm vào saved_collections array của user document
        user_doc.saved_collections.append(collection_id)
        batch.update(
            self._collection.document(requester_uid),
            {"saved_collections": fs.ArrayUnion([collection_id])},
        )
        # Tạo document con trong sub-collection "saved_collections" để lưu thông tin chi tiết về lần lưu này
        saved_collection_doc = SavedCollectionDocument(
            collection_id=collection_id, saved_at=self._current_timestamp
        )

        batch.set(
            self._collection.document(requester_uid)
            .collection("saved_collections")
            .document(collection_id),
            saved_collection_doc.model_dump(mode="python"),
        )

        await self._commit_batch(batch)

        return True

    async def unsave_collection(self, requester_uid: str, collection_id: str) -> bool:
        """Xóa một collection khỏi danh sách đã lưu của user"""
        user_doc = await self.get_user(requester_uid)
        batch = self._db.batch()
        if collection_id not in user_doc.saved_collections:
            raise BadRequestError("Collection not in saved list")

        # Xóa khỏi saved_collections array của user document
        user_doc.saved_collections.remove(collection_id)
        batch.update(
            self._collection.document(requester_uid),
            {"saved_collections": fs.ArrayRemove([collection_id])},
        )
        # Xóa document con trong sub-collection "saved_collections"
        batch.delete(
            self._collection.document(requester_uid)
            .collection("saved_collections")
            .document(collection_id)
        )

        await self._commit_batch(batch)

        return True

    async def suggest_users(self, query: str) -> list[UserDocument]:
        """Gợi ý người dùng dựa trên chuỗi truy vấn."""
        if not query:
            raise ValidationError("Query string cannot be empty")

        # Tìm kiếm người dùng có username_lower khớp với truy vấn (không phân biệt hoa thường)
        query_lower = query.lower()
        docs = (
            await self._collection.where(
                filter=FieldFilter("username_lower", ">=", query_lower)
            )
            .where(filter=FieldFilter("username_lower", "<=", query_lower + "\uf8ff"))
            .limit(5)
            .get()
        )

        suggested_users = []
        for doc in docs:
            try:
                user_doc = UserDocument.model_validate(doc.to_dict())
                suggested_users.append(user_doc)
            except PydanticValidationError as e:
                logger.error(f"Error validating user data for uid {doc.id}: {str(e)}")

        return suggested_users


user_repo = UserRepository()
