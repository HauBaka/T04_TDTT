from schemas.discover_schema import DiscoverHotel
class GeohashRepository:
    def __init__(self):
        pass

    @staticmethod
    def encode(lat: float, lon: float, precision: int = 12, radius: float = 0.0) -> str:
        """Mã hóa tọa độ địa lý thành geohash."""
        return "EHEHE"

    @staticmethod
    def decode(geohash: str) -> tuple[float, float]:
        """Giải mã geohash thành tọa độ địa lý."""
        return (0.0, 0.0) # Mock response
    
    async def search_places(self, lat: float, lon: float, precision: int = 12, radius: float = 0.0) -> list[DiscoverHotel]:
        """Tìm kiếm địa điểm trên database dựa trên query."""
        return [] # Mock response

geohash_repo = GeohashRepository()