
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ViewTargetType(str, Enum):
    HOTEL = "hotels"
    COLLECTION = "collections"

class TopType(str, Enum):
    WEEKLY = "weekly"
    ALL_TIME = "all_time"
    
class ViewStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_views: int = 0
    weekly_views: int = 0

    year: int | None = None
    week: int | None = None

    last_update: datetime | None = None

class ViewLogDocument(BaseModel):
    """view_logs/{log_id=userid_targettype_targetid}"""
    model_config = ConfigDict(from_attributes=True)

    viewer_id: str
    target_id: str

    target_type: ViewTargetType

    last_update: datetime
    
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

