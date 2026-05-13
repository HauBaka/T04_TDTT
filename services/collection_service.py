from datetime import datetime, timezone

from google.cloud import firestore as fs

from core.exceptions import (
    AppException,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
)
from repositories.collection_repo import collection_repo
from repositories.hotel_repo import hotel_repo
from repositories.user_repo import user_repo
from schemas.collection_schema import (
    CollectionContributorResponse,
    CollectionCreateRequest,
    CollectionDocument,
    CollectionPlaceResponse,
    CollectionPublicResponse,
    CollectionResponse,
    CollectionSaverResponse,
    CollectionUpdateRequest,
    CollectionVisibility,
)
from schemas.response_schema import ResponseSchema
from schemas.view_schema import ViewResponse


class CollectionService:
    def __init__(self):
        self.collection_repo = collection_repo

    async def create_collection(self, user_id: str, collection_request: CollectionCreateRequest) -> ResponseSchema[CollectionResponse]:
        """Tạo một collection mới cho người dùng."""
        created_collection = await collection_repo.create_collection(user_id, collection_request)

        return await self.build_response(created_collection)
    
    async def get_collection(self, collection_id: str, requester_id: str | None) -> ResponseSchema[CollectionResponse]:
        """Lấy thông tin của một collection cụ thể."""
        collection = await collection_repo.get_collection(collection_id)

        if collection.visibility == CollectionVisibility.PRIVATE:
            if requester_id != collection.owner_uid and requester_id not in collection.contributor_uids:
                raise PermissionDeniedError(message="You do not have permission to view this collection.")
        
        return await self.build_response(collection)
    
    async def update_collection(self, collection_id: str, requester_id: str, update_data: CollectionUpdateRequest) -> ResponseSchema[CollectionResponse]:
        """Cập nhật thông tin của một collection. Chỉ owner mới có thể cập nhật."""

        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        
        # Check requester - chỉ owner mới có thể update
        owner_uid = collection.owner_uid
        if requester_id != owner_uid:
            raise PermissionDeniedError(message="You do not have permission to edit this collection.")
        
        
        # Check requester user exists
        requester = await user_repo.get_user(requester_id)

        # So sánh với default liked collection
        if collection.id == requester.liked_collection:
            if update_data.name and update_data.name.strip().lower() != "liked":
                raise AppException(status_code=403, message="Cannot change the name of the default collection.")
        
        return await self.build_response(
                await collection_repo.update_collection(collection_id, update_data)
            )
        
    async def add_places_to_collection(self, collection_id: str, requester_id: str, place_ids: list[str]) -> ResponseSchema[CollectionResponse]:
        """Thêm nhiều địa điểm vào một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        
        # Check quyền
        if requester_id != collection.owner_uid and requester_id not in collection.contributor_uids:
            raise PermissionDeniedError(message="You do not have permission to edit this collection.")
        
        # Check place_ids có tồn tại không
        valid_ids = await hotel_repo.valid_ids(place_ids)
        if not valid_ids:
            raise NotFoundError("None of the provided place IDs are valid.")

        # Lọc bỏ những place_id đã tồn tại trong collection để tránh lỗi khi thêm
        existing_place_ids = collection.place_ids
        valid_ids = [pid for pid in valid_ids if pid not in existing_place_ids]

        if not valid_ids:
            raise BadRequestError(message="All provided place IDs are already in the collection.")

        # Thêm vào collection (với lọc duplicate, check existence, lưu vào sub-collection)
        updated_collection = await collection_repo.add_places_to_collection(
            collection_id, 
            valid_ids, 
            requester_id
        )
        
        return await self.build_response(updated_collection)

    async def get_places_from_collection(self, collection_id: str, requester_id: str | None) -> ResponseSchema[list[CollectionPlaceResponse]]:
        """Lấy danh sách chi tiết địa điểm từ một collection."""
        collection = await collection_repo.get_collection(collection_id)

        if collection.visibility == CollectionVisibility.PRIVATE:
            if requester_id != collection.owner_uid and requester_id not in collection.contributor_uids:
                raise PermissionDeniedError(message="You do not have permission to view this collection.")
        
        return ResponseSchema(data=await collection_repo.get_places_from_collection(collection_id))

    async def remove_places_from_collection(self, collection_id: str, requester_id: str, place_ids: list[str]) -> ResponseSchema[CollectionResponse]:
        """Xóa nhiều địa điểm khỏi một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        
        # Check quyền
        if requester_id != collection.owner_uid and requester_id not in collection.contributor_uids:
            raise PermissionDeniedError(message="You do not have permission to edit this collection.")
        
        # Check place_ids có tồn tại không
        valid_ids = await hotel_repo.valid_ids(place_ids)
        if not valid_ids:
            raise NotFoundError("None of the provided place IDs are valid.")

        # Lọc bỏ những place_id không tồn tại trong collection để tránh lỗi khi xóa
        existing_place_ids = collection.place_ids
        valid_ids = [pid for pid in valid_ids if pid in existing_place_ids]
        if not valid_ids:
            raise NotFoundError("None of the provided place IDs are in the collection.")

        # Xóa khỏi collection
        updated_collection = await collection_repo.remove_places_from_collection(collection_id, valid_ids)
        
        return await self.build_response(updated_collection)
    
    async def add_contributors_to_collection(self, collection_id: str, requester_id: str, contributor_uids: list[str]) -> ResponseSchema[CollectionResponse]:
        """Thêm nhiều cộng tác viên vào một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        
        # Check quyền - chỉ owner mới có thể thêm contributors
        if requester_id != collection.owner_uid:
            raise PermissionDeniedError(message="You do not have permission to add contributors to this collection.")
        
        # Validate người dùng tồn tại
        if contributor_uids:
            existing_users = await user_repo.get_users(contributor_uids)
            existing_uids = set(existing_users.keys())
            not_found_uids = [uid for uid in contributor_uids if uid not in existing_uids]
            if not_found_uids:
                raise NotFoundError(f"Invalid contributor UIDs: {', '.join(not_found_uids)}")
        
        # Lấy contributors hiện có
        existing_uids = collection.contributor_uids
        
        # Lọc những uid bị trùng lặp
        new_uids = [uid for uid in contributor_uids if uid not in existing_uids]
        
        if not new_uids:
            raise BadRequestError(message="All provided contributors are already added to the collection.")

        # Thêm vào collection (lưu vào sub-collection với uid, contributed_count, joined_at)
        updated_collection = await collection_repo.add_contributors_to_collection(collection_id, new_uids)
        
        return await self.build_response(updated_collection)

    async def get_contributors_from_collection(self, collection_id: str, requester_id: str | None) -> ResponseSchema[list[CollectionContributorResponse]]:
        """Lấy danh sách chi tiết cộng tác viên từ một collection."""
        collection = await collection_repo.get_collection(collection_id)

        if collection.visibility == CollectionVisibility.PRIVATE:
            if requester_id != collection.owner_uid and requester_id not in collection.contributor_uids:
                raise PermissionDeniedError(message="You do not have permission to view this collection.")
        
        return ResponseSchema(data=await collection_repo.get_contributors_from_collection(collection_id))

    async def remove_contributors_from_collection(self, collection_id: str, requester_id: str, contributor_uids: list[str]) -> ResponseSchema[CollectionResponse]:
        """Xóa nhiều cộng tác viên khỏi một collection. Tránh xóa owner."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        
        # Check quyền - chỉ owner mới có thể xóa contributors
        if requester_id != collection.owner_uid:
            raise PermissionDeniedError(message="You do not have permission to remove contributors from this collection.")
        
        # Kiểm tra không xóa owner
        if collection.owner_uid in contributor_uids:
            raise BadRequestError(message="Cannot remove the owner from contributors.")
        
        # Lấy contributors hiện có
        existing_uids = set(collection.contributor_uids)
        # Lọc những uid không tồn tại trong contributors để tránh lỗi khi xóa
        valid_uids = [uid for uid in contributor_uids if uid in existing_uids]
        if not valid_uids:
            raise NotFoundError("None of the provided contributor UIDs are in the collection.")

        # Xóa khỏi collection
        updated_collection = await collection_repo.remove_contributors_from_collection(collection_id, valid_uids)
        
        return await self.build_response(updated_collection)
    
    async def add_tags_to_collection(self, collection_id: str, requester_id: str, tags: list[str]) -> ResponseSchema[CollectionResponse]:
        """Thêm nhiều tag vào một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        
        # Check quyền
        if requester_id != collection.owner_uid:
            raise PermissionDeniedError(message="Only the owner can add tags to this collection.")
        
        # Lọc tags trùng lặp
        new_tags = [tag for tag in tags if tag not in collection.tags]
        
        # Thêm tags
        updated_collection = await collection_repo.add_tags_to_collection(collection_id, new_tags)
        
        return await self.build_response(updated_collection)

    async def remove_tags_from_collection(self, collection_id: str, requester_id: str, tags: list[str]) -> ResponseSchema[CollectionResponse]:
        """Xóa nhiều tag khỏi một collection."""
        # Check collection có tồn tại không
        collection = await collection_repo.get_collection(collection_id)
        
        # Check quyền
        if requester_id != collection.owner_uid:
            raise PermissionDeniedError(message="Only the owner can remove tags from this collection.")

        # Lọc tags không tồn tại trong collection để tránh lỗi khi xóa
        existing_tags = set(collection.tags)
        valid_tags = [tag for tag in tags if tag in existing_tags]
        if not valid_tags:  
            raise NotFoundError("None of the provided tags are in the collection.")        

        # Xóa tags
        updated_collection = await collection_repo.remove_tags_from_collection(collection_id, valid_tags)
        
        return await self.build_response(updated_collection)

    async def delete_collection(self, collection_id: str, requester_id: str) -> ResponseSchema[bool]:
        """Xóa một collection."""
        collection = await collection_repo.get_collection(collection_id)
        
        # Check requester 
        requester = await user_repo.get_user(requester_id)

        if requester_id != collection.owner_uid:
            raise PermissionDeniedError(message="You do not have permission to delete this collection.")
        
        if collection.id == requester.liked_collection:
            raise BadRequestError(message="Cannot delete the default 'liked' collection.")
        
        return ResponseSchema(data=await collection_repo.delete_collection(collection_id))
    
    async def build_response(
        self,
        collection_data: CollectionDocument
    ) -> ResponseSchema[CollectionResponse]:
        """Xây dựng response cho collection."""
        collection = CollectionPublicResponse(
            id=collection_data.id,
            owner_uid=collection_data.owner_uid,
            name=collection_data.name,
            description=collection_data.description,
            thumbnail_url=collection_data.thumbnail_url,
            created_at=collection_data.created_at,
            updated_at=collection_data.updated_at,
            saved_count=collection_data.saved_count,
            contributor_count=collection_data.contributor_count,
            place_count=collection_data.place_count,
            tags=collection_data.tags,
            visibility=collection_data.visibility,
            views=collection_data.views or ViewResponse()
        )
        return ResponseSchema(data=CollectionResponse(collection=collection))

    async def add_savers_to_collection(self, collection_id: str, requester_id: str) -> ResponseSchema[bool]:
        """Thêm một người dùng vào danh sách đã lưu của collection."""
        # Check collection tồn tại
        collection = await collection_repo.get_collection(collection_id)
        
        # Check user tồn tại
        user = await user_repo.get_user(requester_id)

        saver_ref = collection_repo._collection.document(collection.id).collection("savers").document(user.uid)
        saver_snapshot = await saver_ref.get()
        if saver_snapshot.exists:
            raise BadRequestError(message="Collection already saved.")
        
        batch = collection_repo._db.batch()
        timestamp = datetime.now(timezone.utc)
        
        collection_ref = collection_repo._collection.document(collection.id)
        user_ref = user_repo._collection.document(user.uid)
        
        # Thêm vào savers sub-collection
        saver_ref = collection_ref.collection("savers").document(user.uid)
        batch.set(saver_ref, {
            "uid": user.uid,
            "saved_at": timestamp
        })
        
        # Thêm collection_id vào saved_collections array của user
        batch.update(user_ref, {
            "saved_collections": fs.ArrayUnion([collection.id])
        })
        
        # Tăng saved_count
        batch.update(collection_ref, {
            "saved_count": fs.Increment(1),
            "updated_at": timestamp
        })
        
        await batch.commit()
        return ResponseSchema(data=True)

    async def save_collection(self, collection_id: str, requester_id: str) -> ResponseSchema[bool]:
        """Lưu một collection vào danh sách đã lưu của người dùng."""
        # Check collection tồn tại
        collection = await collection_repo.get_collection(collection_id)
        
        # Check user tồn tại
        user = await user_repo.get_user(requester_id)

        saver_ref = collection_repo._collection.document(collection.id).collection("savers").document(user.uid)
        saver_snapshot = await saver_ref.get()
        if saver_snapshot.exists:
            raise BadRequestError(message="Collection already saved.")
        
        batch = collection_repo._db.batch()
        timestamp = datetime.now(timezone.utc)
        
        collection_ref = collection_repo._collection.document(collection.id)
        user_ref = user_repo._collection.document(user.uid)
        
        # Thêm vào savers sub-collection
        saver_ref = collection_ref.collection("savers").document(user.uid)
        batch.set(saver_ref, {
            "uid": user.uid,
            "saved_at": timestamp
        })
        
        # Thêm collection_id vào saved_collections array của user
        batch.update(user_ref, {
            "saved_collections": fs.ArrayUnion([collection.id])
        })
        
        # Tăng saved_count
        batch.update(collection_ref, {
            "saved_count": fs.Increment(1),
            "updated_at": timestamp
        })
        
        await batch.commit()
        return ResponseSchema(data=True)
    
    async def unsave_collection(self, collection_id: str, requester_id: str) -> ResponseSchema[bool]:
        """Bỏ lưu một collection khỏi danh sách đã lưu của người dùng."""
        # Check collection tồn tại
        collection = await collection_repo.get_collection(collection_id)
        
        # Check user tồn tại
        user = await user_repo.get_user(requester_id)

        saver_ref = collection_repo._collection.document(collection.id).collection("savers").document(user.uid)
        saver_snapshot = await saver_ref.get()
        if not saver_snapshot.exists:
            raise BadRequestError(message="Collection not saved yet.")
        
        batch = collection_repo._db.batch()
        timestamp = datetime.now(timezone.utc)
        
        collection_ref = collection_repo._collection.document(collection.id)
        user_ref = user_repo._collection.document(user.uid)
        
        # Xóa từ savers sub-collection
        saver_ref = collection_ref.collection("savers").document(user.uid)
        batch.delete(saver_ref)
        
        # Xóa collection_id từ saved_collections array của user
        batch.update(user_ref, {
            "saved_collections": fs.ArrayRemove([collection.id])
        })
        
        # Giảm saved_count
        batch.update(collection_ref, {
            "saved_count": fs.Increment(-1),
            "updated_at": timestamp
        })
        
        await batch.commit()
        return ResponseSchema(data=True)

    async def get_savers_from_collection(self, collection_id: str, requester_id: str | None) -> ResponseSchema[list[CollectionSaverResponse]]:
        """Lấy danh sách chi tiết người dùng đã lưu một collection cụ thể."""
        collection = await collection_repo.get_collection(collection_id)

        if collection.visibility == CollectionVisibility.PRIVATE:
            if requester_id != collection.owner_uid and requester_id not in collection.contributor_uids:
                raise PermissionDeniedError(message="You do not have permission to view this collection.")
        
        response = await collection_repo._get_detailed_savers_from_subcollection(collection_id)
        return ResponseSchema(data=list(response.values()))

collection_service = CollectionService()