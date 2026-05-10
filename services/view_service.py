from repositories.view_repo import view_repository
from repositories.collection_repo import collection_repo
from repositories.hotel_repo import hotel_repo
from schemas.collection_schema import CollectionPublic, CollectionVisibility
from schemas.discover_schema import DiscoverHotel
from schemas.view_schema import TopViewRequest, ViewTargetType

class ViewService:
    def __init__(self):
        self.view_repository = view_repository
        self.collection_repo = collection_repo
        self.hotel_repo = hotel_repo

    async def get_top_views(self, data: TopViewRequest) -> list[CollectionPublic | DiscoverHotel]:
        return await self.view_repository.get_top_views(data.target_type, limit=data.limit, page=data.page, top_type=data.top_type)

    async def add_view(self, viewer_id: str, target_id: str, target_type: ViewTargetType) -> None:
        if target_type == ViewTargetType.COLLECTION:
            
            target_doc = await self.collection_repo.get_collection(target_id)
            if not target_doc:
                return

            if target_doc.get("visibility") != CollectionVisibility.PUBLIC.value:
                collaborators = target_doc.get("collaborators", [])
                collaborator_uids = [collaborator.get("uid") for collaborator in collaborators if "uid" in collaborator]

                if target_doc.get("owner_id") != viewer_id or viewer_id not in collaborator_uids:
                    return
        else:
            target_doc = await self.hotel_repo.get_hotels([target_id])
            if not target_doc or len(target_doc) == 0:
                return
            
        await self.view_repository.add_view(viewer_id, target_id, target_type)

view_service = ViewService()
