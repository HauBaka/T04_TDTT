import asyncio

from google.cloud import firestore as fs
from google.cloud.firestore_v1.base_query import FieldFilter
from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from core.cache import cache_delete
from core.exceptions import ValidationError
from repositories.base_repo import BaseRepository
from repositories.hotel_repo import hotel_repo
from repositories.user_repo import user_repo
from schemas.collection_schema import (
    CollectionContributorDocument,
    CollectionContributorResponse,
    CollectionCreateRequest,
    CollectionDocument,
    CollectionPlaceDocument,
    CollectionPlaceResponse,
    CollectionSaverDocument,
    CollectionSaverResponse,
    CollectionUpdateRequest,
)
from schemas.response_schema import UserPreviewResponse
from schemas.user_schema import UserContributingCollectionDocument
from schemas.view_schema import ViewResponse


class CollectionRepository(BaseRepository):
    def __init__(self):
        super().__init__("collections")

    async def create_collection(
        self, uid: str, collection_request: CollectionCreateRequest
    ) -> CollectionDocument:
        """Tạo một collection mới cho người dùng."""
        timestamp = self._current_timestamp

        collection_doc = CollectionDocument(
            id=self._collection.document().id,
            owner_uid=uid,
            name=collection_request.name,
            description=collection_request.description,
            thumbnail_url=collection_request.thumbnail_url,
            created_at=timestamp,
            updated_at=timestamp,
            saved_count=0,
            saver_uids=[],
            contributor_count=0,
            contributor_uids=[],
            place_count=0,
            place_ids=[],
            tags=collection_request.tags or [],
            visibility=collection_request.visibility,
            views=ViewResponse(),
        )
        # Lưu collection mới vào Firestore
        await self._create(
            collection_doc.model_dump(mode="python", exclude_none=False),
            doc_id=collection_doc.id,
        )
        # Tự động thêm creator vào sub-collection contributors
        await self.add_contributors_to_collection(collection_doc.id, [uid])

        return collection_doc

    async def update_collection(
        self,
        collection_id: str,
        update_request: CollectionUpdateRequest,
    ) -> CollectionDocument:
        """Cập nhật một collection của người dùng."""

        payload = update_request.model_dump(mode="python", exclude_none=True)
        if not payload:
            raise ValidationError("No valid fields provided for update.")

        payload["updated_at"] = self._current_timestamp

        await self._update(collection_id, payload)

        return await self.get_collection(collection_id)

    async def delete_collection(self, collection_id: str) -> bool:
        """Xóa một collection của người dùng."""

        ref = self._collection.document(collection_id)

        # Xóa sub-collections trước
        await asyncio.gather(
            self._delete_subcollection(ref.collection("places")),
            self._delete_subcollection(ref.collection("contributors")),
            self._delete_subcollection(ref.collection("savers")),
        )

        # Xóa main document
        batch = self._db.batch()
        batch.delete(ref)
        # Cache invalidate

        await batch.commit()
        await cache_delete(self._build_cache_key("id", collection_id))
        return True

    async def get_collection(self, collection_id: str) -> CollectionDocument:
        """Lấy thông tin của một collection cụ thể."""
        data = await self._get_by_id(collection_id)
        try:
            return CollectionDocument.model_validate(data)
        except PydanticValidationError as e:
            logger.error(
                f"Error validating collection data for {collection_id}: {str(e)}"
            )
            raise ValidationError("Invalid collection data")

    async def _get_places_from_subcollection(
        self, collection_id: str
    ) -> dict[str, CollectionPlaceDocument]:
        """Lấy danh sách places từ sub-collection."""
        try:
            places_ref = self._collection.document(collection_id).collection("places")
            places = {}
            async for doc in places_ref.stream():
                if doc.exists:
                    data = doc.to_dict() or {}
                    data["place_id"] = doc.id
                    try:
                        places[doc.id] = CollectionPlaceDocument.model_validate(data)
                    except PydanticValidationError as e:
                        logger.error(
                            f"Error validating place data for collection {collection_id}: {str(e)}"
                        )
            return places
        except Exception as e:
            logger.error(
                f"Error getting places from subcollection for collection {collection_id}: {str(e)}"
            )
            return {}

    async def _get_contributors_from_subcollection(
        self, collection_id: str
    ) -> dict[str, CollectionContributorDocument]:
        """Lấy danh sách contributors từ sub-collection."""
        try:
            collab_ref = self._collection.document(collection_id).collection(
                "contributors"
            )
            contributors = {}
            async for doc in collab_ref.stream():
                if doc.exists:
                    data = doc.to_dict() or {}
                    data["uid"] = doc.id
                    try:
                        contributors[doc.id] = (
                            CollectionContributorDocument.model_validate(data)
                        )
                    except PydanticValidationError as e:
                        logger.error(
                            f"Error validating contributor data for collection {collection_id}: {str(e)}"
                        )
            return contributors
        except Exception as e:
            logger.error(
                f"Error getting contributors from subcollection for collection {collection_id}: {str(e)}"
            )
            return {}

    async def _get_savers_from_subcollection(
        self, collection_id: str
    ) -> dict[str, CollectionSaverDocument]:
        """Lấy danh sách savers từ sub-collection."""
        try:
            saver_ref = self._collection.document(collection_id).collection("savers")
            savers = {}
            async for doc in saver_ref.stream():
                if doc.exists:
                    data = doc.to_dict() or {}
                    data["uid"] = doc.id
                    try:
                        savers[doc.id] = CollectionSaverDocument.model_validate(data)
                    except PydanticValidationError as e:
                        logger.error(
                            f"Error validating saver data for collection {collection_id}: {str(e)}"
                        )
            return savers
        except Exception as e:
            logger.error(
                f"Error getting savers from subcollection for collection {collection_id}: {str(e)}"
            )
            return {}

    async def _get_detailed_savers_from_subcollection(
        self, collection_id: str
    ) -> dict[str, CollectionSaverResponse]:
        """Lấy danh sách savers chi tiết từ sub-collection."""
        savers = await self._get_savers_from_subcollection(collection_id)
        saver_uids = list(savers.keys())
        saver_responses = {}
        try:
            saver_details = await user_repo.get_users(saver_uids)
            for uid, saver_doc in savers.items():
                user_doc = saver_details.get(uid)
                if user_doc:
                    saver_responses[uid] = CollectionSaverResponse(
                        uid=uid,
                        username=user_doc.username,
                        display_name=user_doc.display_name,
                        avatar_url=user_doc.avatar_url,
                        saved_at=saver_doc.saved_at,
                    )
        except ValidationError:
            logger.info(
                f"Collection {collection_id} has no savers or error validating saver details."
            )

        return saver_responses

    async def add_saver(self, collection_id: str, uid: str) -> CollectionDocument:
        """Thêm một người dùng vào danh sách đã lưu của collection.

        collections/{collection_id}
            saver_uids: [uid_1, uid_2, ...]
            saved_count: int
            ...
            /savers/{uid}
            CollectionSaverDocument

        """
        ref = self._collection.document(collection_id)
        timestamp = self._current_timestamp
        # Lưu thông tin saver vào sub-collection "savers"
        saver_doc = CollectionSaverDocument(uid=uid, saved_at=timestamp)
        batch = self._db.batch()
        batch.set(
            ref.collection("savers").document(uid), saver_doc.model_dump(mode="python")
        )
        # update main document
        batch.update(
            ref,
            {
                "updated_at": timestamp,
                "saved_count": fs.Increment(1),
                "saver_uids": fs.ArrayUnion([uid]),
            },
        )
        await batch.commit()

        return await self.get_collection(collection_id)

    async def remove_saver(self, collection_id: str, uid: str) -> CollectionDocument:
        """Xóa một người dùng khỏi danh sách đã lưu của collection."""
        ref = self._collection.document(collection_id)
        timestamp = self._current_timestamp

        batch = self._db.batch()
        # Xóa thông tin saver khỏi sub-collection "savers"
        batch.delete(ref.collection("savers").document(uid))
        # update main document
        batch.update(
            ref,
            {
                "updated_at": timestamp,
                "saved_count": fs.Increment(-1),
                "saver_uids": fs.ArrayRemove([uid]),
            },
        )
        await batch.commit()

        return await self.get_collection(collection_id)

    async def add_places_to_collection(
        self, collection_id: str, place_ids: list[str], requester_id: str
    ) -> CollectionDocument:
        """Thêm nhiều địa điểm vào collection với lọc duplicate và check existence."""
        ref = self._collection.document(collection_id)
        collection = await self.get_collection(collection_id)
        # Lưu places vào sub-collection
        timestamp = self._current_timestamp
        batch = self._db.batch()
        places_subcollection = ref.collection("places")

        for place_id in place_ids:
            place_ref = places_subcollection.document(place_id)
            place = CollectionPlaceDocument(
                place_id=place_id, added_at=timestamp, added_by=requester_id
            )
            batch.set(place_ref, place.model_dump(mode="python"))

        # Update contributed_count của cộng tác viên trong sub-collection "contributors"
        collab_ref = ref.collection("contributors").document(requester_id)
        batch.update(collab_ref, {"contributed_count": fs.Increment(len(place_ids))})
        # Update contributed_count trong users/{uid}/contributing_collections sub-collection
        user_collab_ref = (
            self._db.collection("users")
            .document(requester_id)
            .collection(
                "contributing_collections"
                if requester_id != collection.owner_uid
                else "owned_collections"
            )
            .document(collection_id)
        )
        batch.update(
            user_collab_ref, {"contributed_count": fs.Increment(len(place_ids))}
        )
        # Update place_count trên main document
        batch.update(
            ref,
            {
                "updated_at": timestamp,
                "place_count": fs.Increment(len(place_ids)),
                "place_ids": fs.ArrayUnion(place_ids),
            },
        )

        await self._commit_batch(batch)
        return await self.get_collection(collection_id)

    async def get_places_from_collection(
        self, collection_id: str
    ) -> list[CollectionPlaceResponse]:
        """Lấy danh sách chi tiết địa điểm từ collection."""
        places = await self._get_places_from_subcollection(collection_id)
        place_ids = list(places.keys())
        place_details = await hotel_repo.get_hotels(place_ids) if place_ids else {}
        contributors: list[
            CollectionContributorResponse
        ] = await self.get_contributors_from_collection(collection_id)
        place_responses = []

        for place_id, place_doc in places.items():
            hotel_doc = place_details.get(place_id)
            contributor_info = next(
                (
                    contributor
                    for contributor in contributors
                    if contributor.uid == place_doc.added_by
                ),
                None,
            )
            if hotel_doc:
                place_responses.append(
                    CollectionPlaceResponse(
                        place_id=place_id,
                        added_at=place_doc.added_at,
                        added_by=UserPreviewResponse(
                            uid=contributor_info.uid,
                            username=contributor_info.username,
                            display_name=contributor_info.display_name,
                            avatar_url=contributor_info.avatar_url,
                        )
                        if contributor_info
                        else None,
                        name=hotel_doc.name,
                        description=hotel_doc.description,
                        link=hotel_doc.link,
                        address=hotel_doc.address,
                        phone=hotel_doc.phone,
                        gps_coordinates=hotel_doc.gps_coordinates,
                        check_in_time=hotel_doc.check_in_time,
                        check_out_time=hotel_doc.check_out_time,
                        price=hotel_doc.price,
                        deal=hotel_doc.deal,
                        booking_sources=hotel_doc.booking_sources,
                        images=hotel_doc.images,
                        amenities=hotel_doc.amenities,
                        raw_rating=hotel_doc.raw_rating,
                        user_reviews=hotel_doc.user_reviews,
                        ai_sentiment=hotel_doc.ai_sentiment,
                        ai_summary=hotel_doc.ai_summary,
                        views=hotel_doc.views,
                    )
                )
        return place_responses

    async def remove_places_from_collection(
        self, collection_id: str, place_ids: list[str]
    ) -> CollectionDocument:
        """Xóa nhiều địa điểm khỏi collection từ sub-collection."""
        ref = self._collection.document(collection_id)
        collection = await self.get_collection(collection_id)
        batch = self._db.batch()
        places_subcollection = ref.collection("places")
        hotels = await self._get_places_from_subcollection(collection_id)

        removing_places = [
            hotel for hotel in hotels.values() if hotel.place_id in place_ids
        ]
        # Update contributed_count của người đã thêm place
        for hotel in removing_places:
            added_by = hotel.added_by
            if not added_by:
                continue
            # Update contributed_count của cộng tác viên trong sub-collection "contributors"
            collab_ref = ref.collection("contributors").document(added_by)
            batch.update(collab_ref, {"contributed_count": fs.Increment(-1)})
            # Update contributed_count trong users/{uid}/contributing_collections sub-collection
            user_collab_ref = (
                self._db.collection("users")
                .document(added_by)
                .collection(
                    "contributing_collections"
                    if added_by != collection.owner_uid
                    else "owned_collections"
                )
                .document(collection_id)
            )
            batch.update(user_collab_ref, {"contributed_count": fs.Increment(-1)})
            # Xóa place khỏi collection
            batch.delete(places_subcollection.document(hotel.place_id))

        # Update place_count trên main document
        batch.update(
            ref,
            {
                "updated_at": self._current_timestamp,
                "place_count": fs.Increment(-len(place_ids)),
                "place_ids": fs.ArrayRemove(place_ids),
            },
        )

        await self._commit_batch(batch)
        return await self.get_collection(collection_id)

    async def add_contributors_to_collection(
        self, collection_id: str, contributor_uids: list[str]
    ) -> CollectionDocument:
        """Thêm nhiều người đóng góp vào collection và lưu vào sub-collection."""
        ref = self._collection.document(collection_id)
        collection = await self.get_collection(collection_id)
        timestamp = self._current_timestamp
        batch = self._db.batch()

        collab_collection = ref.collection("contributors")
        for uid in contributor_uids:
            # Lưu contributors vào sub-collection "contributors"
            collab_ref = collab_collection.document(uid)
            contributor = CollectionContributorDocument(
                uid=uid, contributed_count=0, joined_at=timestamp
            )
            batch.set(collab_ref, contributor.model_dump(mode="python"))

            # Lưu vào users/{uid}/contributing_collections hoặc owned_collections  sub-collection để dễ truy vấn ngược
            user_collab_ref = (
                self._db.collection("users")
                .document(uid)
                .collection(
                    "contributing_collections"
                    if uid != collection.owner_uid
                    else "owned_collections"
                )
                .document(collection_id)
            )
            contributing_doc = UserContributingCollectionDocument(
                collection_id=collection_id, contributed_count=0, joined_at=timestamp
            )
            batch.set(user_collab_ref, contributing_doc.model_dump(mode="python"))

        # Update contributors_count trên main document
        batch.update(
            ref,
            {
                "updated_at": timestamp,
                "contributor_count": fs.Increment(len(contributor_uids)),
                "contributor_uids": fs.ArrayUnion(contributor_uids),
            },
        )

        await self._commit_batch(batch)
        return await self.get_collection(collection_id)

    async def get_contributors_from_collection(
        self, collection_id: str
    ) -> list[CollectionContributorResponse]:
        """Lấy danh sách chi tiết cộng tác viên từ collection."""
        contributors = await self._get_contributors_from_subcollection(collection_id)
        contributor_uids = list(contributors.keys())
        contributor_details = await user_repo.get_users(contributor_uids)

        contributor_responses = []

        for uid, contributor_doc in contributors.items():
            user_doc = contributor_details.get(uid)
            if user_doc:
                contributor_responses.append(
                    CollectionContributorResponse(
                        uid=uid,
                        username=user_doc.username,
                        display_name=user_doc.display_name,
                        avatar_url=user_doc.avatar_url,
                        contributed_count=contributor_doc.contributed_count,
                        joined_at=contributor_doc.joined_at,
                    )
                )

        return contributor_responses

    async def remove_contributors_from_collection(
        self, collection_id: str, contributor_uids: list[str]
    ) -> CollectionDocument:
        """Xóa nhiều người đóng góp khỏi collection từ sub-collection."""
        ref = self._collection.document(collection_id)
        collection = await self.get_collection(collection_id)
        # Lấy những place do contributors đã thêm
        places = await self._get_places_from_subcollection(collection_id)
        removing_places = [
            place for place in places.values() if place.added_by in contributor_uids
        ]

        # Xóa những place do contributors đã thêm
        batch = self._db.batch()
        for place in removing_places:
            batch.delete(ref.collection("places").document(place.place_id))

        collab_collection = ref.collection("contributors")

        for uid in contributor_uids:
            # Xóa những contributors được chỉ định ra khỏi sub-collection "contributors"
            collab_ref = collab_collection.document(uid)
            batch.delete(collab_ref)

            # Xóa collection khỏi users/{uid}/contributing_collections sub-collection
            user_collab_ref = (
                self._db.collection("users")
                .document(uid)
                .collection(
                    "contributing_collections"
                    if uid != collection.owner_uid
                    else "owned_collections"
                )
                .document(collection_id)
            )
            batch.delete(user_collab_ref)
        # Update contributors_count trên main document
        batch.update(
            ref,
            {
                "updated_at": self._current_timestamp,
                "contributor_count": fs.Increment(-len(contributor_uids)),
                "contributor_uids": fs.ArrayRemove(contributor_uids),
            },
        )

        await self._commit_batch(batch)
        return await self.get_collection(collection_id)

    async def add_tags_to_collection(
        self, collection_id: str, new_tags: list[str]
    ) -> CollectionDocument:
        """Thêm nhiều tag vào collection."""
        ref = self._collection.document(collection_id)

        # Dùng ArrayUnion để tránh duplicate tự động
        update_payload = {
            "tags": fs.ArrayUnion(new_tags),
            "updated_at": self._current_timestamp,
        }

        await ref.update(update_payload)
        return await self.get_collection(collection_id)

    async def remove_tags_from_collection(
        self, collection_id: str, tags_to_remove: list[str]
    ) -> CollectionDocument:
        """Xóa nhiều tag khỏi collection."""
        ref = self._collection.document(collection_id)

        # Dùng ArrayRemove để xóa tags
        update_payload = {
            "tags": fs.ArrayRemove(tags_to_remove),
            "updated_at": self._current_timestamp,
        }

        await ref.update(update_payload)
        return await self.get_collection(collection_id)

    # TODO: Chuyển 3 cái get này sang user_repo
    async def get_user_liked_collections(self, uid: str) -> list[CollectionDocument]:
        """Lấy danh sách collections mà người dùng đã thích."""
        query = (
            self._db.collection_group("saved_collections")
            .where(filter=FieldFilter("uid", "==", uid))
            .order_by("saved_at", direction=fs.Query.DESCENDING)
        )

        liked_data = []

        async for like_doc in query.stream():
            collection_ref = like_doc.reference.parent.parent

            if collection_ref is None:
                continue

            liked_data.append(
                {"meta": like_doc.to_dict() or {}, "task": collection_ref.get()}
            )

        docs = await asyncio.gather(
            *[item["task"] for item in liked_data], return_exceptions=True
        )

        collections: list[CollectionDocument] = []

        for item, doc in zip(liked_data, docs):
            if isinstance(doc, BaseException):
                logger.error(f"Error fetching liked collection: {str(doc)}")
                continue

            if not doc.exists:
                continue

            data = doc.to_dict() or {}
            data["id"] = doc.id
            try:
                collections.append(CollectionDocument.model_validate(data))
            except PydanticValidationError as e:
                logger.error(
                    f"Error validating liked collection data for {doc.id}: {str(e)}"
                )
                continue

        return collections

    async def get_user_collections(self, uid: str) -> list[CollectionDocument]:
        """Lấy danh sách collections mà người dùng sở hữu."""
        query = self._collection.where(
            filter=FieldFilter("owner_uid", "==", uid)
        ).order_by("created_at", direction=fs.Query.DESCENDING)
        collections: list[CollectionDocument] = []
        async for doc in query.stream():
            if doc.exists:
                data = doc.to_dict() or {}
                data["id"] = doc.id
                try:
                    collections.append(CollectionDocument.model_validate(data))
                except PydanticValidationError as e:
                    logger.error(
                        f"Error validating collection data for {doc.id}: {str(e)}"
                    )
        return collections

    async def get_contributed_collections(self, uid: str) -> list[CollectionDocument]:
        """Lấy collections mà user tham gia đóng góp, không bao gồm owner."""
        query = (
            self._db.collection_group("contributors")
            .where(filter=FieldFilter("uid", "==", uid))
            .order_by("joined_at", direction=fs.Query.DESCENDING)
        )

        contributor_data = []

        async for contributor_doc in query.stream():
            collection_ref = contributor_doc.reference.parent.parent

            if collection_ref is None:
                continue

            contributor_data.append(
                {"meta": contributor_doc.to_dict() or {}, "task": collection_ref.get()}
            )

        docs = await asyncio.gather(
            *[item["task"] for item in contributor_data], return_exceptions=True
        )

        collections: list[CollectionDocument] = []

        for item, doc in zip(contributor_data, docs):
            if isinstance(doc, BaseException):
                logger.error(f"Error fetching contributed collection: {str(doc)}")
                continue

            if not doc.exists:
                continue

            data = doc.to_dict() or {}

            if data.get("owner_uid") == uid:
                continue

            data["id"] = doc.id
            try:
                collections.append(CollectionDocument.model_validate(data))
            except PydanticValidationError as e:
                logger.error(
                    f"Error validating contributed collection data for {doc.id}: {str(e)}"
                )
                continue

        return collections

    async def get_saved_collections(self, uid: str) -> list[CollectionDocument]:
        """Lấy collections mà user đã lưu."""
        query = (
            self._db.collection_group("savers")
            .where(filter=FieldFilter("uid", "==", uid))
            .order_by("saved_at", direction=fs.Query.DESCENDING)
        )

        saver_data = []

        async for saver_doc in query.stream():
            collection_ref = saver_doc.reference.parent.parent

            if collection_ref is None:
                continue

            saver_data.append(
                {"meta": saver_doc.to_dict() or {}, "task": collection_ref.get()}
            )

        docs = await asyncio.gather(
            *[item["task"] for item in saver_data], return_exceptions=True
        )

        collections: list[CollectionDocument] = []

        for item, doc in zip(saver_data, docs):
            if isinstance(doc, BaseException):
                logger.error(f"Error fetching saved collection: {str(doc)}")
                continue

            if not doc.exists:
                continue

            data = doc.to_dict() or {}
            data["id"] = doc.id
            try:
                collections.append(CollectionDocument.model_validate(data))
            except PydanticValidationError as e:
                logger.error(
                    f"Error validating saved collection data for {doc.id}: {str(e)}"
                )
                continue

        return collections


collection_repo = CollectionRepository()
