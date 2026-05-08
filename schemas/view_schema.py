
from enum import Enum

from pydantic import BaseModel

class ViewTargetType(str, Enum):
    HOTEL = "hotels"
    COLLECTION = "collections"

class TopType(str, Enum):
    WEEKLY = "weekly"
    ALL_TIME = "all_time"

class TopViewRequest(BaseModel):
    limit: int = 10
    page: int = 1
    target_type: ViewTargetType
    top_type: TopType = TopType.ALL_TIME

class AddViewRequest(BaseModel):
    target_id: str
    target_type: ViewTargetType

class ViewResponse(BaseModel):
    total_views: int = 0
    weekly_views: int = 0

