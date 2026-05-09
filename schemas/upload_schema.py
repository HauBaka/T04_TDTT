from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, PositiveInt

class UploadStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"

class UploadCategory(str, Enum):
    AVATAR = "avatar"
    COLLECTION_COVER = "collection_cover"
    GENERIC = "generic"

class UploadPresignRequest(BaseModel): # Request body khi client yêu cầu presign URL để upload file lên R2
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=3, max_length=100) # e.g. image/jpeg
    file_size: PositiveInt
    category: UploadCategory = UploadCategory.GENERIC

class UploadPresignResponse(BaseModel): # Response trả về khi client yêu cầu presign URL để upload file lên R2
    upload_url: str
    file_key: str
    public_url: str
    expires_at: str

class UploadConfirmRequest(BaseModel): # Request body khi client thông báo đã upload file thành công lên R2 và muốn xác nhận để lưu metadata vào DB
    file_key: str = Field(..., min_length=5, max_length=1024)
    file_size: PositiveInt
    etag: Optional[str] = None


class UploadConfirmResponse(BaseModel): # Response trả về khi client xác nhận việc upload file thành công
    file_key: str
    public_url: str
    size_bytes: int
    content_type: str