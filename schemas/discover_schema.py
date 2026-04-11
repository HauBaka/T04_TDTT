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
    
# Tóm tắt AI cho review
class AIReviewSummary(BaseModel):
    pros: list[str]
    cons: list[str]
    notes: str

# Phương tiện di chuyển đến địa điểm lân cận
class Transportation(BaseModel):
    type: str
    duration: str
    
# Địa điểm lân cận
class NearbyPlace(BaseModel):
    name: str
    transportations: list[Transportation] # Danh sách các phương tiện di chuyển đến địa điểm này

# Review gốc từ người dùng
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
    
    # MỚI
    nearby_places: list[NearbyPlace] # Danh sách các địa điểm lân cận, mỗi địa điểm là một đối tượng NearbyPlace
    user_reviews: list[UserReview] # Danh sách review gốc (chưa phân tích), mỗi review là một đối tượng UserReview
    analyzed_reviews: list[AnalyzedReview] # Danh sách các review đã được phân tích
    trust_weight: float       # Trọng số tin cậy tổng thể của khách sạn (0.0 -> 1.0)
    ai_summary_expiration_date: str # ISO format date string cho ngày hết hạn của ai_summary
    ai_score_expiration_date: str   # ISO format date string cho ngày hết hạn của ai_score
    ai_summary: AIReviewSummary           # Tóm tắt do AI tạo ra, có thể hết hạn và cần được làm mới

class DiscoverResponse(BaseModel):
    data: list[DiscoverHotel] # Danh sách các khách sạn phù hợp, mỗi khách sạn là một dict với thông tin chi tiết