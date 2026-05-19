from fastapi import BackgroundTasks
from repositories.view_repo import view_repository
from repositories.collection_repo import collection_repo
from repositories.hotel_repo import hotel_repo
from schemas.collection_schema import CollectionPublicResponse, CollectionVisibility
from schemas.discover_schema import DiscoverHotel
from schemas.user_behavior_schema import UserBehaviorEventCreateRequest, UserEventType
from typing import cast

from loguru import logger

from repositories.collection_repo import collection_repo
from repositories.hotel_repo import hotel_repo
from repositories.user_repo import user_repo
from repositories.view_repo import view_repository
from schemas.collection_schema import (
    CollectionDocument,
    CollectionOwnerResponse,
    CollectionPublicResponse,
    CollectionVisibility,
)
from schemas.discover_schema import DiscoverHotel, HotelDocument
from schemas.view_schema import TopViewRequest, ViewTargetType
from services.behavior_service import behavior_service


class ViewService:
    def __init__(self):
        self.view_repository = view_repository
        self.collection_repo = collection_repo
        self.hotel_repo = hotel_repo

    async def get_top_views(
        self, data: TopViewRequest
    ) -> list[CollectionPublicResponse | DiscoverHotel]:
        result_docs = await self.view_repository.get_top_views(
            data.target_type, limit=data.limit, page=data.page, top_type=data.top_type
        )

        result_responses = []
        if data.target_type == ViewTargetType.COLLECTION:
            collection_docs = cast(list[CollectionDocument], result_docs)
            owner_uids = list(set([doc.owner_uid for doc in collection_docs]))
            owner_docs = await user_repo.get_users(owner_uids) if owner_uids else {}
            owner_responses = {
                uid: CollectionOwnerResponse(
                    uid=doc.uid,
                    username=doc.username,
                    display_name=doc.display_name,
                    avatar_url=doc.avatar_url,
                )
                for uid, doc in owner_docs.items()
            }
            empty_owner_response = CollectionOwnerResponse(
                uid="",
                username="",
                display_name="Unknown",
                avatar_url="",
            )
            for doc in collection_docs:
                result_responses.append(
                    CollectionPublicResponse(
                        id=doc.id,
                        owner=owner_responses.get(doc.owner_uid, empty_owner_response),
                        name=doc.name,
                        description=doc.description,
                        thumbnail_url=doc.thumbnail_url,
                        created_at=doc.created_at,
                        updated_at=doc.updated_at,
                        saved_count=doc.saved_count,
                        contributor_count=doc.contributor_count,
                        place_count=doc.place_count,
                        views=doc.views,
                        tags=doc.tags,
                        visibility=doc.visibility,
                    )
                )

        else:
            hotel_docs = cast(list[HotelDocument], result_docs)
            for doc in hotel_docs:
                if not doc:
                    continue
                try:
                    result_responses.append(DiscoverHotel.model_validate(doc))
                except Exception as e:
                    logger.error(
                        f"Error validating hotel doc {doc.property_token}: {e}"
                    )
                    continue

        return result_responses

    async def add_view(
        self, viewer_id: str, target_id: str, target_type: ViewTargetType,background_tasks: BackgroundTasks
    ) -> None:
        if target_type == ViewTargetType.COLLECTION:
            target_doc = await self.collection_repo.get_collection(target_id)
            if target_doc.visibility != CollectionVisibility.PUBLIC:
                collaborators = (
                    await self.collection_repo._get_contributors_from_subcollection(
                        target_id
                    )
                )
                collaborator_uids = list(collaborators.keys())

                if (
                    target_doc.owner_uid != viewer_id
                    and viewer_id not in collaborator_uids
                ):
                    return
        else:
            target_doc = await self.hotel_repo.get_hotels([target_id])
            if not target_doc or len(target_doc) == 0:
                return

        await self.view_repository.add_view(viewer_id, target_id, target_type)

        background_tasks.add_task(
            behavior_service.record_event,
            viewer_id,
            UserBehaviorEventCreateRequest(
                event_type=UserEventType.VIEW,
                target_id=target_id,
                target_name=str(target_type.value),
                metadata={"target_type": str(target_type.value)},
                source="view_service",
            ),
        )

view_service = ViewService()
