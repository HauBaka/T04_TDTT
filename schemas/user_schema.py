from pydantic import BaseModel, Field, model_validator
from datetime import datetime


class UserSchema(BaseModel):
    uid: str
    username: str
    display_name: str
    email: str
    created_at: datetime

# Không cần chỉnh bật/tắt field vì phức tạp quá
class UserPublic(BaseModel):
    username: str
    display_name: str

class UserPrivate(UserPublic):
    email: str | None = None

class UserResponse(BaseModel):
    user: UserPublic | UserPrivate

class UserUpdateRequest(BaseModel):
    display_name: str | None = None
    email: str | None = None
    # Có thể thêm các trường khác như avatar_url, bio, v.v.

