from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


# Tính chất chuyến đi, thay đổi theo từng lần tìm kiếm.
class TravelStyle(str, Enum):
    RELAX = "nghi_duong"
    FAMILY = "gia_dinh"
    WORK = "cong_tac"
    EXPLORE = "kham_pha"
    ROMANTIC = "lang_man"
    LUXURY = "sang_trong"
    BUDGET = "tiet_kiem"

# Schema lưu trữ các tiêu chí tìm kiếm chuyến đi của người dùng
class TripSearchCriteria(BaseModel):
    budget_min: int | None = None
    budget_max: int | None = None
    trip_style: TravelStyle = TravelStyle.EXPLORE
    party_size: int | None = None
