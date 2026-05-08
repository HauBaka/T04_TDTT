from repositories.view_repo import view_repository
from schemas.collection_schema import CollectionPublic
from schemas.discover_schema import DiscoverHotel
from schemas.view_schema import TopViewRequest, ViewTargetType
class ViewService:
    def __init__(self):
        self.view_repository = view_repository

    async def get_top_views(self, data: TopViewRequest) -> list[CollectionPublic | DiscoverHotel]:
        return await self.view_repository.get_top_views(data.target_type, limit=data.limit, page=data.page, top_type=data.top_type)

    async def add_view(self, viewer_id: str, target_id: str, target_type: ViewTargetType) -> None:
        await self.view_repository.add_view(viewer_id, target_id, target_type)

view_service = ViewService()
