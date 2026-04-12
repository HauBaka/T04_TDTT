from ast import main

import pandas as pd
import random
from pathlib import Path
from pydantic import BaseModel, Field

class UserReview(BaseModel):
    text: str
    raw_stars: float

class DiscoverHotel(BaseModel):
    name: str #thêm tên để phân biệt
    user_reviews: list[UserReview] = Field(default_factory = list)

# Xử lý Virtual Reviews
class VirtualReview:
    def __init__(self, source_path: str):
        """khởi tạo và nạp dữ liệu từ file vào ds virtual_reviews"""
        self.source_path = Path(source_path)
        if not self.source_path.exists():
            raise FileNotFoundError(f"không tìm thấy file: {source_path}")

        df = pd.read_csv(self.source_path)
        self.virtual_reviews: list[UserReview] = [UserReview(text = row['Review'],raw_stars = float(row['Rating'])) for _,row in df.iterrows()]
        print(f"Đã nạp {len(self.virtual_reviews)} review ảo vào dữ liệu)")
    
    def add_random_reviews(self, place: DiscoverHotel, min_count: int, max_count: int):
        """Lấy ngẫu nhiên review từ kho ảo và thêm vào object DiscoverHotel"""
        
        # 1. Check hết data ảo lên đầu trước
        available_count = len(self.virtual_reviews)
        if available_count == 0:
            return

        # 2. Tính số lượng ngẫu nhiên muốn lấy
        # Chặn luôn trường hợp min_count/max_count âm để tránh lỗi hàm random
        requested_count = random.randint(max(0, min_count), max(0, max_count))

        # 3. Nếu data ảo ít hơn thì dùng hết sạch số đang có (Cap count)
        # Không in lỗi, tự điều chỉnh số lượng thực tế
        actual_count = min(requested_count, available_count)

        if actual_count > 0:
            # 4. Lấy mẫu và thêm vào object hotel
            sampled_reviews = random.sample(self.virtual_reviews, actual_count)
            place.user_reviews.extend(sampled_reviews)
            print(f"Done: +{actual_count} reviews cho {place.name}")
    

        
     
