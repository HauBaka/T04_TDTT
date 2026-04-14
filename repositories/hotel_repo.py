from loguru import logger

from schemas.discover_schema import DiscoverHotel
from core.database import get_db
import asyncio
from datetime import datetime, timezone
class HotelRepository:
    def __init__(self):
        self.hotel_collection = "hotels"
        self.BATCH_LIMIT = 490 # Tối đa chỉ được 500 document trong một batch

    def _get_db(self):
        return get_db()
    
    async def upsert_hotel(self, hotel: DiscoverHotel):
        if not hotel.property_token:
            return

        hotel.last_updated = datetime.now(timezone.utc)

        ref = self._get_db().collection(self.hotel_collection).document(hotel.property_token)

        data = hotel.model_dump(exclude_none=True)
        if "added_at" not in data:
            data["added_at"] = hotel.last_updated.isoformat()

        await ref.set(data, merge=True)

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

        for hotel in hotels:
            if not hotel.property_token:
                continue
            
            hotel.last_updated = datetime.now(timezone.utc)

            ref = self._get_db().collection(self.hotel_collection).document(hotel.property_token)

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

hotel_repo = HotelRepository()