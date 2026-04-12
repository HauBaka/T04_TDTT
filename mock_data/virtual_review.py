import pandas as pd
import random
from pathlib import Path
from schemas.discover_schema import DiscoverHotel, UserReview
from loguru import logger

class VirtualReview:
    def __init__(self):
        self.source_path = None
        self.virtual_reviews: list[UserReview] = []

    def initialize(self, source_path: str):
        """khởi tạo và nạp dữ liệu từ file vào ds virtual_reviews"""
        self.source_path = Path(source_path)
        if not self.source_path.exists():
            raise FileNotFoundError(f"Virtual review source file not found: {self.source_path}")

        df = pd.read_csv(self.source_path)
        self.virtual_reviews = [UserReview(text = row['Review'],raw_stars = float(row['Rating'])) for _,row in df.iterrows()]

        logger.info(f"Imported {len(self.virtual_reviews)} virtual reviews from {self.source_path}")

    def add_random_reviews(self, place: DiscoverHotel, min_count: int, max_count: int):
        """Lấy ngẫu nhiên review từ kho và thêm vào object DiscoverHotel"""
        
        # 1. Check hết data ảo
        available_count = len(self.virtual_reviews)
        if available_count == 0:
            logger.warning(f"No virtual reviews available for {place.name}")
            return
        
        min_count = max(0, min_count) # Chặn âm
        max_count = max(0, max_count) # Chặn âm
        # Chặn trường hợp min_count > max_count
        if min_count > max_count:
            logger.warning(f"Invalid count range: min_count ({min_count}) > max_count ({max_count}). Adjusting to min_count = max_count.")
            min_count = max_count

        # 2. Tính số lượng ngẫu nhiên muốn lấy
        requested_count = random.randint(min_count, max_count)

        # 3. Nếu data ảo ít hơn thì dùng hết
        actual_count = min(requested_count, available_count)

        if actual_count > 0:
            sampled_reviews = random.sample(self.virtual_reviews, actual_count)
            place.user_reviews.extend(sampled_reviews)

virtual_review_manager = VirtualReview()