from pydantic import BaseModel, Field
from datetime import datetime
from schemas.collection_schema import CollectionPublic
from schemas.user_preference_schema import ScoringWeights, UserBehaviorEvent, UserTravelPreference


class UserSchema(BaseModel):
    uid: str
    username: str
    display_name: str
    email: str
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
    display_name: str | None = None
    email: str | None = None
    # Có thể thêm các trường khác như avatar_url, bio, v.v.

