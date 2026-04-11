from transformers import pipeline
import re
import logging
import asyncio
from schemas.discover_schema import AnalyzedReview

logger = logging.getLogger(__name__)

class SentimentService:
    def __init__(self):
        # Khởi tạo PhoBERT (Chỉ load 1 lần khi khởi động Server để tránh lag)
        try:
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis", 
                model="wonrax/phobert-base-vietnamese-sentiment",
                device=-1 # Chạy trên CPU
            )
        except Exception as e:
            logger.error(f"Lỗi khi tải PhoBERT: {str(e)}")
            self.sentiment_analyzer = None

    async def _analyze_sentiment(self, text: str) -> float:
        """
        Gọi PhoBERT để phân tích cảm xúc văn bản tiếng Việt.
        """
        if not self.sentiment_analyzer:
            return 3.0

        try:
            # Model trả về dạng: [{'label': 'POS', 'score': 0.987}]
            result = self.sentiment_analyzer(text)[0]
            label = result['label']
            confidence = result['score'] # Giá trị từ 0.0 đến 1.0
            
            # Khởi tạo điểm mặc định là trung bình
            final_score = 3.0 
            
            if label == 'POS':
                # Càng tự tin là Tích cực -> Điểm càng tiến gần về 5.0
                final_score = 3.0 + (confidence * 2.0)
                
            elif label == 'NEG':
                # Càng tự tin là Tiêu cực -> Điểm càng tiến gần về 1.0
                final_score = 3.0 - (confidence * 2.0)
                
            elif label == 'NEU':
                # Nếu là trung tính, giữ điểm lân cận 3.0
                final_score = 3.0
                
            # Đảm bảo điểm số luôn nằm trong giới hạn an toàn và làm tròn 1 chữ số thập phân
            return round(min(max(final_score, 1.0), 5.0), 1)
                
        except Exception as e:
            logger.error(f"Lỗi khi chạy PhoBERT với text '{text}': {str(e)}")
            return 3.0

    def _check_vague(self, text: str) -> bool:
        """
        Kiểm tra review có quá chung chung, vô nghĩa hoặc spam không.
        """
        # 1. Xóa ký tự đặc biệt và chuyển chữ thường
        cleaned = re.sub(r'[^\w\s]', '', text).strip().lower()
        words = cleaned.split()
        
        # 2. Lọc độ dài (Quá ngắn)
        if len(words) < 3:
            return True
            
        # 3. Chống Spam lặp từ ("ok ok ok ok")
        unique_words = set(words)
        if len(unique_words) <= 2 and len(words) >= 4:
            # Nếu câu dài hơn 4 chữ nhưng lại chỉ có 1-2 từ khác nhau
            return True
            
        # 4. Chống từ vô nghĩa dài bất thường
        # Nếu có chữ dài > 15 ký tự thường là spam "ahhhhhhhh" hoặc gõ bậy "asdfghjkl"
        if any(len(word) > 15 for word in words):
            return True

        return False

    async def calculate_real_rating(self, raw_reviews: list[dict]) -> tuple[float, float, list[AnalyzedReview]]:
        """
        Hàm này nhận vào danh sách review gốc (mỗi review là dict có 'text' và 'raw_stars') và trả về:
        - Điểm đánh giá thực tế đã được điều chỉnh (float)
        - Trọng số tin cậy trung bình của các review (float)
        - Danh sách review đã được phân tích chi tiết (list of AnalyzedReview)
        """
        
        if not raw_reviews:
            return 0.0, 0.0, []

        # 1. Tách dữ liệu để xử lí song song với asyncio
        texts = [rev.get("text", "") for rev in raw_reviews]
        
        # Tạo danh sách các coroutines để gọi PhoBERT
        sentiment_tasks = [self._analyze_sentiment(text) for text in texts]
        
        # Chạy tất cả cùng một lúc thay vì đợi từng cái
        sentiment_scores = await asyncio.gather(*sentiment_tasks)

        analyzed_list = []
        total_weighted_stars = 0.0
        total_weight = 0.0

        # 2. Xử lý từng review cùng với điểm sentiment tương ứng để tính điểm điều chỉnh và trọng số tin cậy
        for rev, sentiment_score in zip(raw_reviews, sentiment_scores):
            text = rev.get("text", "")
            raw_stars = float(rev.get("raw_stars", 3.0))

            # Kiểm tra vague
            is_vague = self._check_vague(text)
            trust_weight = 0.2 if is_vague else 1.0
            adjusted_stars = raw_stars

            # Đối soát Logic
            if not is_vague:
                if sentiment_score >= 4.0 and raw_stars <= 2.0:
                    # Khen nhưng bấm nhầm sao thấp
                    adjusted_stars = (sentiment_score + raw_stars) / 2.0 + 1.0
                elif sentiment_score <= 2.0 and raw_stars >= 4.0:
                    # Chê thậm tệ nhưng cho sao cao (seeding/buff bẩn)
                    trust_weight = 0.1
                    adjusted_stars = sentiment_score

            # Chuẩn hóa điểm số về khoảng [1.0 - 5.0]
            adjusted_stars = round(min(max(adjusted_stars, 1.0), 5.0), 1)

            # Cập nhật kết quả
            analyzed_list.append(
                AnalyzedReview(
                    text=text,
                    raw_stars=raw_stars,
                    sentiment_score=sentiment_score,
                    trust_weight=trust_weight,
                    adjusted_stars=adjusted_stars
                )
            )

            total_weighted_stars += adjusted_stars * trust_weight
            total_weight += trust_weight

        # 3. Kết quả cuối cùng là điểm trung bình có điều chỉnh và trọng số tin cậy trung bình
        final_real_rating = total_weighted_stars / total_weight if total_weight > 0 else 0.0
        avg_trust = total_weight / len(raw_reviews)

        return round(final_real_rating, 2), round(avg_trust, 2), analyzed_list