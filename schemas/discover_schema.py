from pydantic import BaseModel, Field, model_validator
from datetime import date, datetime, timezone
from typing import Annotated

# ==============================
# CÁC CLASS REQUEST & VALIDATION
# ==============================
class DiscoverRequest(BaseModel):
    language: str # để tạm
    address: str
    check_in: datetime
    check_out: datetime
    min_price: int
    max_price: int
    children: list[Annotated[int, Field(ge=1, le=17)]] | None = None  # Tuổi của trẻ em, ví dụ: [5, 8] nếu có 2 trẻ em 5 và 8 tuổi
    adults: int
    personality: str # để tạm
    
    # Thêm ràng buộc
    @model_validator(mode='after')
    def validate_cross_fields(self) -> 'DiscoverRequest':
        # Đổi timezone của check_in và check_out về UTC để so sánh chính xác hơn
        self.check_in = self.check_in.astimezone(timezone.utc)
        self.check_out = self.check_out.astimezone(timezone.utc)
        # 1. Ràng buộc ngày tháng: today <= check_in < check_out
        if self.check_in < datetime.now(timezone.utc):
            raise ValueError("check_in must be today or later.")
        
        if self.check_in >= self.check_out:
            raise ValueError("check_in must be before check_out.")
            
        # 2. Ràng buộc giá: min_price < max_price
        if self.min_price >= self.max_price:
            raise ValueError("min_price must be less than max_price.")
            
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
    overview: str | None = None
    pros: list[str] | None = None
    cons: list[str] | None = None
    notes: str | None = None

# Review gốc từ người dùng
class UserReview(BaseModel):
    text: str
    raw_stars: float

# ==========================================
# CÁC CLASS DATA KHÁC
# ==========================================

class WeatherInfo(BaseModel):
    """Schema lưu trữ thông tin thời tiết tại điểm đến"""
    
    condition: str # trạng thái thời tiết (VD: Trời nắng, Mưa to, Nhiều mây)
    temp_c: float # nhiệt độ thực tế
    temp_feels_like: float # nhiệt độ cảm nhận thực tế
    rain_chance: int # Xác suất có mưa

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
    type: str | None = None
    distance: str | None = None
    duration: str | None = None

# Địa điểm lân cận
class NearbyPlace(BaseModel):
    category: str | None = None
    name: str
    thumbnail: str | None = None
    description: str | None = None
    gps_coordinates: GPSCoordinates | None = None
    transportations: list[Transportation] = [] # Danh sách các phương tiện di chuyển đến địa điểm này

class DiscoverHotel(BaseModel):
    # thông itn cơ bản
    property_token: str | None = None
    name: str
    description: str | None = None
    link: str | None = None
    address: str | None = None
    phone: str | None = None
    gps_coordinates: GPSCoordinates | None = None
    nearby_places: list[NearbyPlace] = [] # Danh sách các địa điểm lân cận

    # Nhận phòng & Trả phòng
    check_in_time: str | None = None
    check_out_time: str | None = None

    price: float # json_data -> rate_per_night.extracted_lowest
    deal: str | None = None
    booking_sources: list[BookingSource] = [] # Danh sách giá ở các trang khác

    # ảnh & Tiện ích
    images: list[HotelImage] = [] 
    amenities: list[str] = []

    # Reviews gốc
    raw_rating: float = 0.0 # trung bình từ các user reviews
    user_reviews: list[UserReview] = [] # Danh sách review gốc (chưa phân tích)

    # Ai phân tích lại
    ai_score: float = 0.0
    trust_weight: float  = 0.0     # Trọng số tin cậy tổng thể của khách sạn (0.0 -> 1.0)
    analyzed_reviews: list[AnalyzedReview] = [] # Danh sách các review đã được phân tích
    ai_score_expiration_date: datetime | None = None  # ISO format date string cho ngày hết hạn của ai_score
    ai_summary_expiration_date: datetime | None = None # ISO format date string cho ngày hết hạn của ai_summary
    ai_summary: AIReviewSummary | None = None     # Tóm tắt do AI tạo ra, có thể hết hạn và cần được làm mới

    # updates
    last_updated: datetime | None = None

class DiscoverResponse(BaseModel):
    data: list[DiscoverHotel] # Danh sách các khách sạn phù hợp, mỗi khách sạn là một dict với thông tin chi tiết