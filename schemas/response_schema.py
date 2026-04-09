from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar('T')

class ResponseSchema(BaseModel, Generic[T]):
    status_code: int = 200 # Default to 200 OK
    message: str = "Success" # Default
    data: Optional[T] = None