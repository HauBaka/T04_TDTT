from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from schemas.collection_schema import CollectionPublicResponse
from schemas.user_preference_schema import ScoringWeights, UserTravelPreference


class UserDocument(BaseModel):
    """users/{uid}"""

    model_config = ConfigDict(from_attributes=True)

    # Thông tin định danh
    uid: str
    username: str
    username_lower: str
    email: str
    # Thông tin cá nhân (hiển thị)
    display_name: str
    avatar_url: str | None = None
    bio: str | None = Field(None, max_length=500)
    # Thông tin cá nhân (không hiển thị)
    liked_collection: str  # Collection này dùng để lưu danh sách vị trí yêu thích, không xem là collection thực sự
    owned_collections: list[str] = Field(default_factory=list)
    contributing_collections: list[str] = Field(default_factory=list)
    saved_collections: list[str] = Field(default_factory=list)
    conversations: list[str] = Field(default_factory=list)

    chatbot_conversation: str
    phone_number: str | None = Field(None, max_length=10)
    # Thông tin về thời gian
    created_at: datetime
    last_login: datetime | None = None
    last_updated: datetime | None = None
    # Các trường thông tin cá nhân khác có thể thêm vào đây

    # collections: list[CollectionPublicResponse] = Field(default_factory=list)
    # user_behavior_history: list[UserBehaviorEvent] = Field(default_factory=list)

    # Trip hiện tại mà user đang tham gia
    current_trip: str | None = None
    travel_profile: UserTravelPreference | None = None
    scoring_weights: ScoringWeights | None = None


class SavedCollectionDocument(BaseModel):
    """Thông tin về collection đã được user lưu.
    users/{uid}/saved_collections/{collection_id}
    """

    collection_id: str
    saved_at: datetime


class UserCreateRequest(BaseModel):
    uid: str
    username: str
    username_lower: str
    email: str
    phone_number: str | None = Field(None, max_length=10)

    display_name: str
    avatar_url: str | None = None
    bio: str | None = Field(None, max_length=500)

    liked_collection: str
    chatbot_conversation: str

    created_at: datetime = Field(default_factory=datetime.now)
    last_login: datetime | None = None
    last_updated: datetime | None = None


# Không cần chỉnh bật/tắt field vì phức tạp quá
class UserPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    uid: str
    username: str

    display_name: str
    avatar_url: str | None = None
    bio: str | None = Field(None, max_length=500)

    last_login: datetime | None = None


class UserPrivateResponse(UserPublicResponse):
    email: str | None = None

    liked_collection: str | None = None
    chatbot_conversation: str
    phone_number: str | None = Field(None, max_length=10)

    created_at: datetime
    last_updated: datetime | None = None
    last_login: datetime | None = None

    current_trip: str | None = None

    travel_profile: UserTravelPreference | None = None
    scoring_weights: ScoringWeights | None = None


class UserUpdateRequest(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=16)
    email: str | None = Field(None, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")

    display_name: str | None = Field(None, min_length=3, max_length=32)
    avatar_url: str | None = None
    bio: str | None = Field(None, max_length=500)

    phone_number: str | None = Field(None, max_length=10)


class UserCollectionsResponse(BaseModel):
    liked: list[CollectionPublicResponse] = Field(default_factory=list)
    owned: list[CollectionPublicResponse] = Field(default_factory=list)
    collaborated: list[CollectionPublicResponse] = Field(default_factory=list)


class UserSavedCollectionDocument(BaseModel):
    """users/{uid}/saved_collections/{collection_id}"""

    collection_id: str
    saved_at: datetime


class UserContributingCollectionDocument(BaseModel):
    """users/{uid}/contributing_collections/{collection_id}"""

    collection_id: str
    contributed_count: int = 0
    joined_at: datetime


class UserOwnedCollectionDocument(BaseModel):
    """users/{uid}/owned_collections/{collection_id}"""

    collection_id: str
    created_at: datetime


class UserSaveCollectionRequest(BaseModel):
    collection_id: str


class AddFavouritePlaceRequest(BaseModel):
    place_id: str
