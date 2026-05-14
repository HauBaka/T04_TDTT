"""Tinh toán khoảng cách giữa hai điểm địa lý sử dụng công thức Haversine"""

import math

from schemas.response_schema import GPSCoordinates


def haversine_distance(place1: GPSCoordinates, place2: GPSCoordinates) -> float | None:
    """Tính khoảng cách giữa hai điểm GPS (lat1, lon1) và (lat2, lon2) trả về kết quả bằng km"""
    if not place1 or not place2:
        return None

    R = 6371  # Bán kính Trái Đất tính bằng km

    phi1 = math.radians(place1.latitude)
    phi2 = math.radians(place2.latitude)
    delta_phi = math.radians(place2.latitude - place1.latitude)
    delta_lambda = math.radians(place2.longitude - place1.longitude)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
