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
    
# Review sau khi phân tích cảm xúc
class AnalyzedReview(BaseModel):
    text: str
    raw_stars: float
    sentiment_score: float    # Điểm do PhoBERT chấm
    trust_weight: float       # Trọng số tin cậy của review (0.0 -> 1.0)
    adjusted_stars: float     # Điểm sau khi đối soát (kết hợp raw_stars và sentiment_score)

class DiscoverHotel(BaseModel):
    name: str
    address: str
    price: int
    raw_rating: float
    amenities: list[str]
    description: str
    ai_overview: str
    ai_score: float   
    
    # MỚI
    analyzed_reviews: list[AnalyzedReview] # Danh sách các review đã được phân tích
    trust_weight: float       # Trọng số tin cậy tổng thể của khách sạn (0.0 -> 1.0)

class DiscoverResponse(BaseModel):
    data: list[DiscoverHotel] # Danh sách các khách sạn phù hợp, mỗi khách sạn là một dict với thông tin chi tiết