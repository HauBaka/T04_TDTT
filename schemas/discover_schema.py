from pydantic import BaseModel
from datetime import date
class DiscoverRequest(BaseModel):
    language: str
    address: str
    check_in: date
    check_out: date
    min_price: int
    max_price: int
    amenities: list[str]
    children: list[int] # Tuổi của trẻ em, ví dụ: [5, 8] nếu có 2 trẻ em 5 và 8 tuổi
    adults: int
    personality: str

class UserReview(BaseModel):
    text: str
    raw_stars: float

class DiscoverHotel(BaseModel):
    name: str
    address: str
    price: int
    raw_rating: float
    amenities: list[str]
    description: str
    ai_overview: str
    ai_score: float

    user_reviews: list[UserReview] = []
class DiscoverResponse(BaseModel):
    data: list[DiscoverHotel] # Danh sách các khách sạn phù hợp, mỗi khách sạn là một dict với thông tin chi tiết