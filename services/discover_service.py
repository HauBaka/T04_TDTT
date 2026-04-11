from core.exceptions import *
from datetime import datetime, timezone
from schemas.discover_schema import DiscoverRequest, DiscoverHotel
from services.sentiment_service import SentimentService

CACHE_EXPIRATION_DAYS = 7

class DiscoverService:
    def __init__(self, payload: DiscoverRequest):
        self.payload = payload
        self.sentiment_service = SentimentService()

    async def raw_search(self) -> list[DiscoverHotel]:
        """Gọi SerpAPI để lấy dữ liệu thô dựa trên payload đầu vào"""
        return []
    async def hard_filter(self) -> list[DiscoverHotel]:
        """Lọc dữ liệu thô theo các tiêu chí cứng"""
        return []
    
    async def process_places_real_rating(self, filtered_places: list[DiscoverHotel]) -> list[DiscoverHotel]:
        """
        Với mỗi khách sạn trong filtered_places, kiểm tra xem đã có điểm đánh giá thực tế (real_rating) và trọng số tin cậy (trust_weight) trong Firebase chưa:
        - Nếu có và còn hạn (cập nhật trong vòng 7 ngày), lấy từ Firebase.
        - Nếu không có hoặc đã hết hạn, gọi SentimentService để tính toán lại điểm đánh giá thực tế dựa trên review gốc, sau đó cập nhật lại vào Firebase.  
        """
        
        collection_ref = None # Chỗ này sẽ là tham chiếu đến collection trong Firebase, ví dụ: get_db().collection("hotel_ratings")

        for place in filtered_places:
            property_token = None # Dùng cái gì đó để làm token định danh khách sạn

            doc_ref = collection_ref.document(property_token)
            doc = doc_ref.get()

            needs_calculation = False 

            if doc.exists:
                data = doc.to_dict()
                last_updated = data.get("last_updated")  # Trường này cần được lưu dưới dạng ISO string hoặc timestamp khi cập nhật vào Firebase    
                
                if last_updated:
                    now = datetime.now(timezone.utc)
                    if isinstance(last_updated, datetime):
                        time_diff = now - last_updated
                    else:
                        time_diff = now - datetime.fromisoformat(str(last_updated))

                    if time_diff.days < CACHE_EXPIRATION_DAYS:
                        # Còn hạn -> Lấy từ DB
                        place.ai_score = data.get("ai_score", 0.0)
                        place.trust_weight = data.get("trust_weight", 0.0)
                        place.analyzed_reviews = data.get("analyzed_reviews", [])
                        continue 
                    else:
                        # Hết hạn
                        needs_calculation = True
                else:
                    needs_calculation = True
            else:
                # Chưa có trong DB
                needs_calculation = True

            # Gọi AI nếu cần thiết
            if needs_calculation:
                raw_reviews = [] # Lấy review gốc từ đâu đó
                if raw_reviews:
                    real_score, avg_trust, analyze_reviews = await self.sentiment_service.calculate_real_rating(raw_reviews)
                    place.ai_score = real_score
                    place.trust_weight = avg_trust
                    place.analyzed_reviews = analyze_reviews # Cập nhật lại review đã phân tích vào place
                    # Cập nhật lại vào Firebase
                    doc_ref.set({
                        "ai_score": real_score,
                        "trust_weight": avg_trust,
                        "analyzed_reviews": analyze_reviews,
                        "last_updated": datetime.now(timezone.utc).isoformat()
                    }, merge=True)
                else:
                    place.ai_score = place.raw_rating
                    place.trust_weight = 0.0
                    place.analyzed_reviews = []

        return filtered_places

    async def execute_discover_pipeline(self, payload: DiscoverRequest) -> list[DiscoverHotel]:
        """Thực thi pipeline tìm kiếm"""
        raw_results = await self.raw_search()
        filtered_results = await self.hard_filter()
        # ...
        return []