from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class UserEventType(str, Enum):
    VIEW = "xem"
    SAVE_PLACE = "luu_place"
    REMOVE_PLACE = "xoa_place"
    SAVE_COLLECTION = "luu_collection"
    REMOVE_COLLECTION = "xoa_collection"


class GetRecentBehaviourEventRequest(BaseModel):
    user_uid: str
    limit: int = 100
    last_doc: Any | None = None


class UserBehaviorEventCreateRequest(BaseModel):
    event_type: UserEventType
    target_id: str | None = None
    target_name: str | None = None
    metadata: dict[str, str] | None = None
    source: str | None = None


class UserBehaviorEventDocument(BaseModel):
    id: str
    user_uid: str
    event_type: UserEventType
    target_id: str | None = None
    target_name: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str] = Field(default_factory=dict)
