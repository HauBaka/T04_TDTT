from core.exceptions import *
from datetime import datetime, timezone, timedelta
from schemas.discover_schema import DiscoverRequest, DiscoverHotel, AIReviewSummary
from services.sentiment_service import SentimentService
from services.summary_service import SummaryService
from utils.parse_expiration_date import parse_expiration_date
import asyncio

REAL_RATING_CACHE_EXPIRATION_DAYS=7
SUMMARY_CACHE_EXPIRATION_DAYS = 14 

class DiscoverService:
    def __init__(self, payload: DiscoverRequest):
        self.payload = payload
        self.sentiment_service = SentimentService()
        self.summary_service = SummaryService()

    async def raw_search(self) -> list[DiscoverHotel]:
        """Gọi SerpAPI để lấy dữ liệu thô dựa trên payload đầu vào"""
        return []
    async def hard_filter(self) -> list[DiscoverHotel]:
        """Lọc dữ liệu thô theo các tiêu chí cứng"""
        return []
    
    async def process_places_real_rating(self, filtered_places: list[DiscoverHotel]) -> list[DiscoverHotel]:
        """
        Xử lý điểm đánh giá thực tế cho từng khách sạn trong danh sách đã lọc. Cụ thể:
        Với mỗi khách sạn trong filtered_places, kiểm tra xem đã có điểm đánh giá thực tế (ai_score) và ngày hết hạn của điểm đó (ai_score_expiration_date):
            - Nếu có và còn hạn (cập nhật trong vòng 7 ngày), lấy điểm đánh giá thực tế
            - Nếu không có hoặc đã hết hạn, gọi SentimentService để tính điểm đánh giá thực tế mới dựa trên review gốc và phân tích cảm xúc
        """
        
        if not filtered_places:
            return []
        
        sentiment_tasks = []
        places_needing_calculation = []
        now = datetime.now(timezone.utc)

        for place in filtered_places:
            needs_calculation = False 
            expiration_date_str = getattr(place, "ai_score_expiration_date", None)
            has_cache = hasattr(place, "analyzed_reviews") and len(place.analyzed_reviews) > 0

            if has_cache and expiration_date_str:
                try:
                    expiration_date = parse_expiration_date(expiration_date_str)
                    # Kiểm tra còn hạn hay không
                    if now >= expiration_date:
                        # Đã vượt quá ngày hết hạn -> Cần tính lại
                        needs_calculation = True
                except (ValueError, TypeError):
                    # Lỗi định dạng ngày tháng -> Bắt buộc tính lại
                    needs_calculation = True
            else:
                # Chưa có điểm đánh giá thực tế hoặc chưa có ngày hết hạn -> Cần tính lại
                needs_calculation = True
            

            # Gọi AI nếu cần thiết
            if needs_calculation:
                # Lấy raw_reviews (danh sách UserReview) từ object
                raw_reviews = getattr(place, "user_reviews", [])
                
                # Đưa vào hàng đợi để gọi AI song song
                task = self.sentiment_service.calculate_real_rating(raw_reviews)
                sentiment_tasks.append(task)
                places_needing_calculation.append(place)

        # Thực thi tất cả các tác vụ AI cùng lúc
        if sentiment_tasks:
            results = await asyncio.gather(*sentiment_tasks, return_exceptions=True)
            new_expiration_date = (now + timedelta(days=REAL_RATING_CACHE_EXPIRATION_DAYS)).isoformat()
            # Cập nhật kết quả vào từng place tương ứng
            for place, result in zip(places_needing_calculation, results):
                if isinstance(result, Exception):
                    
                    # Nếu có lỗi khi gọi AI, gán mặc định tạm thời để tránh bị kẹt 7 ngày không có điểm đánh giá nào cả
                    place.ai_score = place.raw_rating  # Hoặc có thể gán một giá trị mặc định nào đó
                    place.analyzed_reviews = []
                    place.ai_score_expiration_date = now.isoformat()
                    place.trust_weight = 0.0
                    continue

                real_rating, trust_weight, analyzed_reviews = result
                place.ai_score = real_rating
                place.trust_weight = trust_weight
                place.analyzed_reviews = analyzed_reviews
                place.ai_score_expiration_date = new_expiration_date

        return filtered_places
    
    async def process_places_ai_summary(self, filtered_places: list[DiscoverHotel]) -> list[DiscoverHotel]:
        """
        Module này sẽ đảm nhiệm việc tạo tóm tắt AI cho từng khách sạn dựa trên review đã phân tích, tiện ích và vị trí lân cận. Cụ thể:
        Với mỗi khách sạn trong filtered_places, kiểm tra xem đã có tóm tắt AI (ai_summary) và ngày hết hạn của tóm tắt đó (ai_summary_expiration_date):
            - Nếu có và còn hạn (cập nhật trong vòng 14 ngày), lấy tóm tắt
            - Nếu không có hoặc đã hết hạn, gọi SummaryService để tạo tóm tắt mới dựa trên review đã phân tích, tiện ích và vị trí lân cận
        """
        
        if not filtered_places:
            return []

        ai_tasks = []
        places_needing_summary = []
        now = datetime.now(timezone.utc)

        for place in filtered_places:
            # Lấy dữ liệu cần thiết để gọi AI Summary
            user_reviews = getattr(place, "analyzed_reviews", [])
            amenities = getattr(place, "amenities", [])
            nearby_places = getattr(place, "nearby_places", [])
            
            hotel_name = place.name 
            
            needs_ai_call = False

            # 2. Kiểm tra đã có ai_summary và ai_summary_expiration_date chưa
            ai_summary = getattr(place, "ai_summary", None)
            expiration_date_str = getattr(place, "ai_summary_expiration_date", None)

            if ai_summary and expiration_date_str:
                try:
                    expiration_date = parse_expiration_date(expiration_date_str)
                    
                    # Kiểm tra ai_summary còn hạn hay không
                    if now >= expiration_date:
                        # Đã vượt quá ngày hết hạn -> Cần gọi AI
                        needs_ai_call = True
                except (ValueError, TypeError):
                    # Lỗi định dạng ngày tháng -> Bắt buộc tính lại
                    needs_ai_call = True
            else:
                # Chưa có ai_summary -> Cần gọi AI
                needs_ai_call = True

            # Chuẩn bị luồng gọi AI nếu cần thiết
            if needs_ai_call:
                # Tạo coroutine cho việc gọi AI Summary, nhưng chưa chạy ngay mà sẽ chạy cùng lúc ở bước sau để tối ưu hiệu suất
                task = self.summary_service.generate_places_summary(
                    analyzed_reviews=user_reviews,
                    hotel_name=hotel_name,
                    amenities=amenities,
                    nearby_places=nearby_places
                )
                ai_tasks.append(task)
                places_needing_summary.append(place)

        # Thực thi tất cả các tác vụ AI Summary cùng lúc
        if ai_tasks:
            # Chờ tất cả AI tasks chạy xong cùng lúc
            summaries_results = await asyncio.gather(*ai_tasks, return_exceptions=True)

            # Tính toán ngày hết hạn mới cho những place được update
            new_expiration_date = (now + timedelta(days=SUMMARY_CACHE_EXPIRATION_DAYS)).isoformat()

            # Cập nhật kết quả AI vào từng place tương ứng
            for place, summary in zip(places_needing_summary, summaries_results):
                if isinstance(summary, Exception):
                    # Nếu Gemini lỗi, gán mặc định tạm thời để tránh bị kẹt 14 ngày không có tóm tắt nào cả
                    place.ai_summary = AIReviewSummary(
                        pros=["Lỗi hệ thống khi tải tóm tắt ưu điểm."],
                        cons=["Lỗi hệ thống khi tải tóm tắt nhược điểm."],
                        notes="Không thể tổng hợp bằng AI lúc này."
                    )
                    # Đặt ngày hết hạn là thời điểm hiện tại (now) để lần tìm kiếm sau nó tự động gọi lại AI thay vì bị kẹt 14 ngày
                    place.ai_summary_expiration_date = now.isoformat()
                    continue

                # Cập nhật kết quả AI vào Place
                place.ai_summary = summary
                place.ai_summary_expiration_date = new_expiration_date

        return filtered_places

    async def execute_discover_pipeline(self, payload: DiscoverRequest) -> list[DiscoverHotel]:
        """Thực thi pipeline tìm kiếm"""
        raw_results = await self.raw_search()
        filtered_results = await self.hard_filter()
        # ...
        return []