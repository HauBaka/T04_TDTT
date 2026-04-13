from pydantic import BaseModel, Field, model_validator
from datetime import date, datetime, timezone
from typing import Annotated

# ==============================
# CÁC CLASS REQUEST & VALIDATION
# ==============================
class DiscoverRequest(BaseModel):
    language: str
    address: str
    check_in: datetime
    check_out: datetime
    min_price: int
    max_price: int
    amenities: list[str] = []
    children: list[Annotated[int, Field(ge=1, le=17)]] = [] # Tuổi của trẻ em, ví dụ: [5, 8] nếu có 2 trẻ em 5 và 8 tuổi
    adults: int
    personality: str
    
    # Thêm ràng buộc
    @model_validator(mode='after')
    def validate_cross_fields(self) -> 'DiscoverRequest':
        # 1. Ràng buộc ngày tháng: today <= check_in < check_out
        if self.check_in < datetime.now(timezone.utc):
            raise ValueError("Ngày check_in không được trong quá khứ (today <= check_in).")
        
        if self.check_in >= self.check_out:
            raise ValueError("Ngày check_in phải diễn ra trước ngày check_out (check_in < check_out).")
            
        # 2. Ràng buộc giá: min_price < max_price
        if self.min_price >= self.max_price:
            raise ValueError("Giá trị min_price phải nhỏ hơn max_price.")
            
        return self

# ==============================
# CÁC CLASS AI & REVIEWS
# ==============================

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

# Review gốc từ người dùng
class UserReview(BaseModel):
    text: str
    raw_stars: float

# ==========================================
# CÁC CLASS DATA KHÁC
# ==========================================

class GPSCoordinates(BaseModel):
    latitude: float
    longitude: float

class HotelImage(BaseModel):
    thumbnail: str | None = None
    original_image: str | None = None

class BookingSource(BaseModel):
    """Giá khi book tại các trang khác (Agoda, Booking,...)"""
    source: str
    logo: str | None = None
    link: str | None = None
    price: int | None = None # Lấy từ rate_per_night.extracted_lowest

# Phương tiện di chuyển đến địa điểm lân cận
class Transportation(BaseModel):
    type: str
    duration: str
    
# Địa điểm lân cận
class NearbyPlace(BaseModel):
    category: str | None = None
    name: str
    thumbnail: str | None = None
    rating: float | None = None
    reviews: int | None = None
    description: str | None = None
    gps_coordinates: GPSCoordinates | None = None
    transportations: list[Transportation] = [] # Danh sách các phương tiện di chuyển đến địa điểm này

class DiscoverHotel(BaseModel):
    # thông itn cơ bản
    property_token: str | None = None
    name: str
    description: str | None = None
    link: str | None = None
    address: str
    phone: str | None = None
    gps_coordinates: GPSCoordinates | None = None
    nearby_places: list[NearbyPlace] = [] # Danh sách các địa điểm lân cận

    # Nhận phòng & Trả phòng
    check_in_time: str | None = None
    check_out_time: str | None = None

    price: int # json_data -> rate_per_night.extracted_lowest
    deal: str | None = None
    booking_sources: list[BookingSource] = [] # Danh sách giá ở các trang khác

    # ảnh & Tiện ích
    images: list[HotelImage] = [] 
    amenities: list[str] = []

    # Reviews gốc
    raw_rating: float = 0.0 # trung bình từ các user reviews
    user_reviews: list[UserReview] = [] # Danh sách review gốc (chưa phân tích)

    # Ai phân tích lại
    ai_overview: str | None = None
    ai_score: float = 0.0
    trust_weight: float       # Trọng số tin cậy tổng thể của khách sạn (0.0 -> 1.0)
    analyzed_reviews: list[AnalyzedReview] = [] # Danh sách các review đã được phân tích
    ai_score_expiration_date: datetime | None   # ISO format date string cho ngày hết hạn của ai_score
    ai_summary_expiration_date: datetime | None # ISO format date string cho ngày hết hạn của ai_summary
    ai_summary: AIReviewSummary | None      # Tóm tắt do AI tạo ra, có thể hết hạn và cần được làm mới


class DiscoverResponse(BaseModel):
    data: list[DiscoverHotel] # Danh sách các khách sạn phù hợp, mỗi khách sạn là một dict với thông tin chi tiết