from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional, Dict, Any


class UserSchema(BaseModel):
    uid: str
    username: str
    display_name: str
    email: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length = 500)

# Không cần chỉnh bật/tắt field vì phức tạp quá
class UserPublic(BaseModel):
    username: str
    display_name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

class UserPrivate(UserPublic):
    email: str | None = None

class UserResponse(BaseModel):
    user: UserPublic | UserPrivate

class UserUpdateRequest(BaseModel):
    display_name: str | None = None
    email: str | None = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length = 500)
    # Có thể thêm các trường khác như avatar_url, bio, v.v.


