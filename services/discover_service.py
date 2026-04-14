from core.exceptions import *
from datetime import datetime, timezone, timedelta
from schemas.discover_schema import DiscoverRequest, DiscoverHotel, AIReviewSummary
from services.sentiment_service import sentiment_service
from services.summary_service import SummaryService
from mock_data.virtual_review import virtual_review_manager
from externals.SerpAPI import serp_api
from repositories.hotel_repo import hotel_repo
import asyncio
from loguru import logger

REAL_RATING_CACHE_EXPIRATION_DAYS=7
SUMMARY_CACHE_EXPIRATION_DAYS = 14 

class DiscoverService:
    def __init__(self, payload: DiscoverRequest):
        self.payload = payload
        self.sentiment_service = sentiment_service
        self.summary_service = SummaryService()

    async def raw_search(self) -> list[DiscoverHotel]:
        """Gọi SerpAPI để lấy dữ liệu thô dựa trên payload đầu vào"""
        result = await serp_api.search_places(
            query=self.payload.address,
            language=self.payload.language,
            check_in_date=self.payload.check_in.strftime("%Y-%m-%d"),
            check_out_date=self.payload.check_out.strftime("%Y-%m-%d"),
            adults=self.payload.adults,
            children=self.payload.children,
            min_price=self.payload.min_price,
            max_price=self.payload.max_price,
        )
        return result.data or []
      
    async def get_reviews(self, hotels: list[DiscoverHotel]):
        """Lấy review cho từng khách sạn"""
        for hotel in hotels:
            virtual_review_manager.add_random_reviews(hotel, min_count=25, max_count=50)
        # XXX: hơi chậm
        
    async def process_places_real_rating(self, filtered_places: list[DiscoverHotel]):
        """
        Xử lý điểm đánh giá thực tế cho từng khách sạn trong danh sách đã lọc. Cụ thể:
        Với mỗi khách sạn trong filtered_places, kiểm tra xem đã có điểm đánh giá thực tế (ai_score) và ngày hết hạn của điểm đó (ai_score_expiration_date):
            - Nếu có và còn hạn (cập nhật trong vòng 7 ngày), lấy điểm đánh giá thực tế
            - Nếu không có hoặc đã hết hạn, gọi SentimentService để tính điểm đánh giá thực tế mới dựa trên review gốc và phân tích cảm xúc
        """
        
        if not filtered_places or len(filtered_places) == 0:
            return
        
        sentiment_tasks = []
        places_needing_calculation = []
        now = datetime.now(timezone.utc)

        for place in filtered_places:
            expiration_date = place.ai_score_expiration_date # Sử dụng datetime để so sánh, tránh chuyển đổi qua lại giữa string và datetime
            has_cache = len(place.analyzed_reviews) > 0 # Đã có AI review chưa

            if has_cache and (expiration_date and now < expiration_date):
                # Nếu đã có ai review và còn hạn, thì không cần tính lại
                continue

            # Lấy raw_reviews (danh sách UserReview) từ object
            raw_reviews = place.user_reviews # luôn có trường này
            if not raw_reviews or len(raw_reviews) == 0:
                # Nếu không có review nào, không thể tính điểm đánh giá thực tế, gán mặc định để tránh lỗi
                place.ai_score = place.raw_rating 
                place.analyzed_reviews = []
                place.ai_score_expiration_date = now + timedelta(days=REAL_RATING_CACHE_EXPIRATION_DAYS)
                place.trust_weight = 0.0 # Không có review nào -> không đáng tin cậy
                continue

            # Đưa vào hàng đợi để gọi AI xử lí song song
            task = self.sentiment_service.calculate_real_rating(raw_reviews)
            sentiment_tasks.append(task)
            places_needing_calculation.append(place)

        # Thực thi tất cả các tác vụ AI cùng lúc
        if sentiment_tasks:
            results = await asyncio.gather(*sentiment_tasks, return_exceptions=True)
            new_expiration_date = now + timedelta(days=REAL_RATING_CACHE_EXPIRATION_DAYS) # Sử dụng datetime 
            # Cập nhật kết quả vào từng place tương ứng
            for place, result in zip(places_needing_calculation, results):
                if isinstance(result, BaseException):
                    # Nếu có lỗi khi gọi AI, gán mặc định tạm thời để tránh bị kẹt 7 ngày không có điểm đánh giá nào cả
                    place.ai_score = place.raw_rating  # Hoặc có thể gán một giá trị mặc định nào đó
                    place.analyzed_reviews = []
                    place.ai_score_expiration_date = now
                    place.trust_weight = 0.0
                    continue

                # Gán kết quả AI vào Place
                real_rating, trust_weight, analyzed_reviews = result
                place.ai_score = real_rating
                place.trust_weight = trust_weight
                place.analyzed_reviews = analyzed_reviews
                place.ai_score_expiration_date = new_expiration_date
    
    async def process_places_ai_summary(self, filtered_places: list[DiscoverHotel]):
        """
        Module này sẽ đảm nhiệm việc tạo tóm tắt AI cho từng khách sạn dựa trên review đã phân tích, tiện ích và vị trí lân cận. Cụ thể:
        Với mỗi khách sạn trong filtered_places, kiểm tra xem đã có tóm tắt AI (ai_summary) và ngày hết hạn của tóm tắt đó (ai_summary_expiration_date):
            - Nếu có và còn hạn (cập nhật trong vòng 14 ngày), lấy tóm tắt
            - Nếu không có hoặc đã hết hạn, gọi SummaryService để tạo tóm tắt mới dựa trên review đã phân tích, tiện ích và vị trí lân cận
        """
        
        if not filtered_places:
            return

        ai_tasks = []
        places_needing_summary = []
        now = datetime.now(timezone.utc)

        for place in filtered_places:
            # Lấy dữ liệu cần thiết để gọi AI Summary
            user_reviews = place.analyzed_reviews 
            amenities = place.amenities
            nearby_places = place.nearby_places
            
            hotel_name = place.name 
            
            # 2. Kiểm tra đã có ai_summary và ai_summary_expiration_date chưa
            ai_summary = place.ai_summary
            expiration_date = place.ai_summary_expiration_date # Sử dụng datetime

            if ai_summary and expiration_date and now < expiration_date:
                # Nếu đã có tóm tắt và còn hạn, không cần gọi AI
                continue

            # Chuẩn bị luồng gọi AI nếu cần thiết
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
            new_expiration_date = now + timedelta(days=SUMMARY_CACHE_EXPIRATION_DAYS)

            # Cập nhật kết quả AI vào từng place tương ứng
            for place, summary in zip(places_needing_summary, summaries_results):
                if isinstance(summary, Exception):
                    # Nếu Gemini lỗi, gán mặc định tạm thời để tránh bị kẹt 14 ngày không có tóm tắt nào cả
                    place.ai_summary = AIReviewSummary(
                        overview="Không thể tải tóm tắt tổng quan lúc này.",
                        pros=["Lỗi hệ thống khi tải tóm tắt ưu điểm."],
                        cons=["Lỗi hệ thống khi tải tóm tắt nhược điểm."],
                        notes="Không thể tổng hợp bằng AI lúc này."
                    )
                    # Đặt ngày hết hạn là thời điểm hiện tại (now) để lần tìm kiếm sau nó tự động gọi lại AI thay vì bị kẹt 14 ngày
                    place.ai_summary_expiration_date = now
                    continue

                # Cập nhật kết quả AI vào Place
                place.ai_summary = summary
                place.ai_summary_expiration_date = new_expiration_date
        
    async def execute_discover_pipeline(self) -> list[DiscoverHotel]:
        """Thực thi pipeline tìm kiếm"""
        raw_results = await self.raw_search()
        await self.get_reviews(raw_results)
        await self.process_places_real_rating(raw_results)
        # await self.process_places_ai_summary(raw_results) XXX: quá nghèo để có thể gọi AI Summary, tạm thời để sau
        await hotel_repo.upsert_hotels(raw_results)  # Lưu kết quả vào Firestore
        return raw_results