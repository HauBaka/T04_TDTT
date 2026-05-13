from typing import Generic, TypeVar

from schemas.response_schema import ResponseSchema

T = TypeVar("T")


class SerpAPIResultSchema(ResponseSchema[T], Generic[T]):
    next_page_token: str | None = None
