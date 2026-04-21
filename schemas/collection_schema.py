from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class CollectionCollaborator(BaseModel):
    uid: str
    display_name: str
    username: str
    avatar_url: str | None = None
    contributed_count: int = 0 # số lượng địa điểm mà cộng tác viên đã thêm vào collection
    joined_at: datetime # thời điểm cộng tác viên được thêm vào collection

class CollectionPlace(BaseModel):
    place_id: str
    added_at: datetime
    added_by: str  # uid của người dùng đã thêm địa điểm này vào collection

class ModifyAction(str, Enum):
    """Định nghĩa các hành động có thể thực hiện khi cập nhật collection."""
    ADD = "add"
    REMOVE = "remove"

class TargetType(str, Enum):
    PLACE = "place"
    COLLABORATOR = "collaborator"
    TAG = "tag"

class Modification(BaseModel):
    """Định nghĩa cấu trúc dữ liệu cho việc cập nhật collection."""
    target_id: str
    target_type: TargetType  # "place", "collaborator", hoặc "tag"
    action: ModifyAction

class CollectionLiked(BaseModel):
    uid: str
    liked_at: datetime

class CollectionVisibility(str, Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"

class CollectionPublic(BaseModel):
    id: str
    owner_uid: str
    name: str = Field(..., min_length=3, max_length=32)
    description: str | None = Field(None, max_length=512)
    thumbnail_url: str | None = None
    created_at: datetime
    updated_at: datetime
    liked_count: int = 0
    liked: list[CollectionLiked] = Field(default_factory=list)
    collaborators: list[CollectionCollaborator] = Field(default_factory=list)
    places: list[CollectionPlace] = Field(default_factory=list) 
    
    # Các tag do người dùng gắn cho bộ sưu tập
    tags: list[str] = Field(default_factory=list)
    visibility: CollectionVisibility = CollectionVisibility.PUBLIC

class CollectionUnlisted(CollectionPublic):
    pass

class CollectionPrivate(CollectionPublic):
    pass

class CollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=32)
    description: str | None = Field(None, max_length=512)
    tags: list[str] = Field(default_factory=list)
    visibility: CollectionVisibility = CollectionVisibility.PUBLIC
    thumbnail_url: str | None = None

class CollectionUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=32)
    description: str | None = Field(None, max_length=512)
    collaborators: list[Modification] | None = None
    places: list[Modification] | None = None
    tags: list[Modification] | None = None
    visibility: CollectionVisibility | None = None

class CollectionResponse(BaseModel):
    collection: CollectionPublic | CollectionUnlisted | CollectionPrivate