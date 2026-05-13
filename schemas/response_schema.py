from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar('T')

class ResponseSchema(BaseModel, Generic[T]):
    status_code: int = 200 # Default to 200 OK
    message: str = "Success" # Default
    data: Optional[T] = None

class UserPreviewResponse(BaseModel):
    uid: str
    username: str
    display_name: str | None = None
    avatar_url: str | None = None