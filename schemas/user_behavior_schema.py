from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class UserEventType(str, Enum):
    VIEW = "xem"
    SAVE_PLACE = "luu_place"
    REMOVE_PLACE = "xoa_place"
    SAVE_COLLECTION = "luu_collection"
    REMOVE_COLLECTION = "xoa_collection"


class UserBehaviorEvent(BaseModel):
    id: str
    user_id: str
    event_type: UserEventType
    target_id: str | None = None
    target_name: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str] = Field(default_factory=dict)