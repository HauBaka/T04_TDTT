from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional, Dict, Any

class UserSchema(BaseModel):
    uid: str
    username: str
    display_name: str
    email: str
    avatar_url: str | None = None
    bio: str | None = Field(None, max_length=500)

# Không cần chỉnh bật/tắt field vì phức tạp quá
class UserPublic(BaseModel):
    username: str
    display_name: str
    avatar_url: str | None = None
    bio: str | None = None

class UserPrivate(UserPublic):
    email: str | None = None

class UserResponse(BaseModel):
    user: UserPublic | UserPrivate

class UserUpdateRequest(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=16)
    display_name: str | None = Field(None, min_length=3, max_length=32)
    email: str | None = Field(None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    phone_number: str | None = None
    avatar_url: str | None = None
    bio: str | None = Field(None, max_length=500)

