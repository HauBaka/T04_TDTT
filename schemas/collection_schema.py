from pydantic import BaseModel, Field, model_validator
from datetime import date, datetime, timezone
from typing import Annotated
from enum import Enum

class CollectionCollaborator(BaseModel):
    uid: str
    display_name: str
    username: str
    avatar_url: str | None = None

class CollectionVisibility(str, Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"

class CollectionPublic(BaseModel):
    id: str
    owner_uid: str
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    collaborators: list[CollectionCollaborator] = []
    places: list[str] = []
    
    # Các tag do người dùng gắn cho bộ sưu tập
    tags: list[str] = Field(default_factory=list)
    visibility: CollectionVisibility = CollectionVisibility.PUBLIC

class CollectionUnlisted(CollectionPublic):
    pass

class CollectionPrivate(CollectionPublic):
    pass

class CollectionCreateRequest(BaseModel):
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    visibility: CollectionVisibility = CollectionVisibility.PUBLIC
    thumbnail_url: str | None = None

class CollectionUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    collaborators: list[CollectionCollaborator] | None = None
    places: list[str] | None = None
    tags: list[str] | None = None
    visibility: CollectionVisibility | None = None

class CollectionResponse(BaseModel):
    collection: CollectionPublic | CollectionUnlisted | CollectionPrivate