from pydantic import BaseModel, Field
from datetime import datetime
from schemas.collection_schema import CollectionPublic
from schemas.user_preference_schema import ScoringWeights, UserBehaviorEvent, UserTravelPreference


class UserSchema(BaseModel):
    uid: str
    username: str
    display_name: str
    email: str
    avatar_url: str | None = None
    bio: str | None = Field(None, max_length=500)
    created_at: datetime
    
    # Các trường thông tin cá nhân khác có thể thêm vào đây
    travel_profile: UserTravelPreference | None = None
    collections: list[CollectionPublic] = Field(default_factory=list)
    user_behavior_history: list[UserBehaviorEvent] = Field(default_factory=list)
    scoring_weights: ScoringWeights | None = None

# Không cần chỉnh bật/tắt field vì phức tạp quá
class UserPublic(BaseModel):
    username: str
    display_name: str
    avatar_url: str | None = None
    bio: str | None = None

class UserPrivate(UserPublic):
    email: str | None = None
    
    # Các trường thông tin cá nhân khác có thể thêm vào đây
    travel_profile: UserTravelPreference | None = None
    collections: list[CollectionPublic] = Field(default_factory=list)
    user_behavior_history: list[UserBehaviorEvent] = Field(default_factory=list)
    scoring_weights: ScoringWeights | None = None

class UserResponse(BaseModel):
    user: UserPublic | UserPrivate

class UserUpdateRequest(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=16)
    display_name: str | None = Field(None, min_length=3, max_length=32)
    email: str | None = Field(None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    phone_number: str | None = None
    avatar_url: str | None = None
    bio: str | None = Field(None, max_length=500)

