from loguru import logger

from core.settings import settings
from schemas.discover_schema import DiscoverHotel
from core.database import get_db
import asyncio
import pygeohash as pgh
from datetime import datetime, timedelta, timezone
from google.cloud.firestore_v1 import FieldFilter
from repositories.base_repo import BaseRepository

class HotelRepository(BaseRepository):
    def __init__(self):
        super().__init__("hotels")
        self.BATCH_LIMIT = 490 # Tối đa chỉ được 500 document trong một batch
    
    async def _commit_batch(self, batch, retries=2):
        for attempt in range(retries + 1):
            try:
                await batch.commit()
                return
            except Exception as e:
                if attempt < retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))  # backoff
                else:
                    logger.error(f"Failed to commit batch after {retries} retries: {str(e)}")

    async def upsert_hotels(self, hotels: list[DiscoverHotel]):
        if not hotels:
            return

        batch = self._get_db().batch()
        count = 0

        now = datetime.now(timezone.utc)
        for hotel in hotels:
            if not hotel.property_token:
                continue
            
            hotel.last_updated = now

            ref = self._collection.document(hotel.property_token)

            data = hotel.model_dump(exclude_none=True)
            if "added_at" not in data:
                data["added_at"] = hotel.last_updated.isoformat()

            batch.set(ref, data, merge=True)

            count += 1

            if count >= self.BATCH_LIMIT: # Chia theo từng batch
                await self._commit_batch(batch)
                batch = self._get_db().batch()
                count = 0

        if count > 0:
            await self._commit_batch(batch)

    async def delete_hotels(self, property_tokens: list[str]):
        if not property_tokens:
            return

        batch = self._get_db().batch()
        count = 0

        for token in property_tokens:
            ref = self._collection.document(token)
            batch.delete(ref)
            count += 1

            if count >= self.BATCH_LIMIT:
                await self._commit_batch(batch)
                batch = self._get_db().batch()
                count = 0

        if count > 0:
            await self._commit_batch(batch)

    async def sync_hotels_background(self, hotels: list[DiscoverHotel]):
        """Hàm chạy ngầm để đồng bộ dữ liệu khách sạn mới tìm được vào database mà không cần chờ FE"""
        try:
            now = datetime.now(timezone.utc)
            expire_threshold = now - timedelta(days=settings.HOTEL_DATA_EXPIRE_DAYS)

            to_upsert = []
            to_delete = []

            for hotel in hotels:
                if not hotel.property_token:
                    continue

                if hotel.last_updated and hotel.last_updated < expire_threshold:
                    to_delete.append(hotel.property_token)
                    continue

                hotel.last_updated = now
                to_upsert.append(hotel)

            await self.upsert_hotels(to_upsert)
            await self.delete_hotels(to_delete)

        except Exception as e:
            logger.error(f"sync_hotels_background error: {str(e)}")

    def _get_neighbors(self, geohash: str):
        lat, lon = pgh.decode(geohash)
        d = 0.04  # offset ~ 4.5km

        neighbors = []
        for dlat in [-d, 0, d]:
            for dlon in [-d, 0, d]:
                if dlat == 0 and dlon == 0:
                    continue
                neighbors.append(pgh.encode(lat + dlat, lon + dlon, precision=settings.GEOHASH_PRECISION))

        return neighbors
    
    async def search_hotels(self, lat: float, lng: float) -> list[DiscoverHotel]:
        """Tìm kiếm khách sạn dựa trên tọa độ và bán kính."""
        center_hash  = pgh.encode(lat, lng, precision=settings.GEOHASH_PRECISION)  # precision=5 cho khoảng 4.9km x 4.9km, có thể điều chỉnh tuỳ nhu cầu
        hashes = [center_hash] + self._get_neighbors(center_hash)
        hotels = []

        seen_ids = set()

        for h in hashes:
            start_hash = h
            end_hash = h + "~"
            docs = self._collection.where(filter=FieldFilter("gps_coordinates.geohash", ">=", start_hash)).where(filter=FieldFilter("gps_coordinates.geohash", "<=", end_hash)).stream()
            
            async for doc in docs:
                if doc.id in seen_ids: # skip repeated document
                    continue

                seen_ids.add(doc.id)

                data = doc.to_dict()
                try:
                    hotel = DiscoverHotel.model_validate(data)
                    hotels.append(hotel)
                except Exception as e:
                    logger.error(f"Error validating hotel data for document {doc.id}: {str(e)}")

        return hotels

    async def get_hotels(self, property_tokens: list[str]) -> dict[str, dict]:
        """Lấy thông tin nhiều khách sạn từ danh sách property tokens."""
        if not property_tokens:
            return {}
        
        try:
            doc_refs = [self._collection.document(token) for token in property_tokens]
            docs = [doc async for doc in self._get_db().get_all(doc_refs)]
            hotels = {doc.id: doc.to_dict() or {} for doc in docs if doc.exists}
            
        except Exception as e:
            logger.error(f"Error fetching hotels: {str(e)}")
            hotels = {}
        return hotels

    async def get_places(self, place_ids: list[str]) -> list[dict]:
        """Lấy thông tin nhiều địa điểm (places) dựa trên place_ids."""
        if not place_ids:
            return []
        
        places = []
        hotel_data = await self.get_hotels(place_ids)
        
        for place_id in place_ids:
            if place_id in hotel_data:
                place_info = hotel_data[place_id].copy()
                place_info['id'] = place_id  # Thêm id vào object
                places.append(place_info)
        
        return places

hotel_repo = HotelRepository()