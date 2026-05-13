import asyncio
from datetime import timedelta

import pygeohash as pgh
from google.cloud.firestore_v1 import FieldFilter
from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import ValidationError
from core.settings import settings
from repositories.base_repo import BaseRepository
from schemas.discover_schema import DiscoverHotel, HotelDocument


class HotelRepository(BaseRepository):
    def __init__(self):
        super().__init__("hotels")
        self.BATCH_LIMIT = 490  # Tối đa chỉ được 500 document trong một batch

    async def upsert_hotels(self, hotels: list[DiscoverHotel]):
        """Thêm mới hoặc cập nhật thông tin nhiều khách sạn cùng lúc.

        Raises:
            ValidationError: Nếu hotels rỗng hoặc lỗi trong quá trình upsert
        """
        if not hotels:
            raise ValidationError("No hotel data provided for upsert")

        batch = self._db.batch()
        count = 0
        now = self._current_timestamp

        for hotel in hotels:
            if not hotel.property_token:
                continue
            try:
                hotel.last_updated = now

                ref = self._collection.document(hotel.property_token)
                hotel_doc = HotelDocument.model_validate(
                    hotel.model_dump(exclude_none=True)
                )

                batch.set(
                    ref,
                    hotel_doc.model_dump(exclude_none=False),  # đảm bảo đúng schema
                    merge=True,
                )

                count += 1

                if count >= self.BATCH_LIMIT:  # Chia theo từng batch
                    await self._commit_batch(batch)
                    batch = self._db.batch()
                    count = 0

            except PydanticValidationError as e:
                logger.error(
                    f"Error validating hotel data for property_token {hotel.property_token}: {str(e)}"
                )
                continue

        if count > 0:
            await self._commit_batch(batch)

    async def delete_hotels(self, property_tokens: list[str]):
        """Xóa nhiều khách sạn dựa trên danh sách property tokens.

        Raises:
            ValidationError: Nếu property_tokens rỗng hoặc lỗi trong quá trình xóa
        """
        if not property_tokens:
            raise ValidationError("No property tokens provided for deletion")

        batch = self._db.batch()
        count = 0

        for token in property_tokens:
            ref = self._collection.document(token)
            batch.delete(ref)
            count += 1

            if count >= self.BATCH_LIMIT:
                await self._commit_batch(batch)
                batch = self._db.batch()
                count = 0

        if count > 0:
            await self._commit_batch(batch)

    async def sync_hotels_background(self, hotels: list[DiscoverHotel]):
        """Hàm chạy ngầm để đồng bộ dữ liệu khách sạn mới tìm được vào database mà không cần chờ FE"""

        if not hotels:
            logger.warning("sync_hotels_background called with empty hotel list")
            return
        try:
            now = self._current_timestamp
            expire_threshold = now - timedelta(
                days=settings.HOTEL_DATA_EXPIRE_DAYS
            )  # Ngày hết hạn của dữ liệu khách sạn cũ

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
        """Lấy geohash của các ô lân cận xung quanh geohash trung tâm để mở rộng phạm vi tìm kiếm.

        Raises:
            ValidationError: Nếu geohash rỗng hoặc không hợp lệ
        """
        if not geohash:
            raise ValidationError("Geohash is required")

        lat, lon = pgh.decode(geohash)
        d = 0.04  # offset ~ 4.5km

        neighbors = []
        for dlat in [-d, 0, d]:
            for dlon in [-d, 0, d]:
                if dlat == 0 and dlon == 0:
                    continue
                neighbors.append(
                    pgh.encode(
                        lat + dlat, lon + dlon, precision=settings.GEOHASH_PRECISION
                    )
                )

        return neighbors

    async def _query_geohash_range(self, geohash: str):
        if not geohash:
            raise ValidationError("Geohash is required for geospatial query")

        start_hash = geohash
        end_hash = geohash + "~"
        docs = (
            self._collection.where(
                filter=FieldFilter("gps_coordinates.geohash", ">=", start_hash)
            )
            .where(filter=FieldFilter("gps_coordinates.geohash", "<=", end_hash))
            .limit(20)
            .stream()
        )
        result = [doc async for doc in docs]
        return result

    async def search_hotels(self, lat: float, lng: float) -> list[DiscoverHotel]:
        """Tìm kiếm khách sạn dựa trên tọa độ và bán kính."""
        center_hash = pgh.encode(
            lat, lng, precision=settings.GEOHASH_PRECISION
        )  # precision=5 cho khoảng 4.9km x 4.9km, có thể điều chỉnh tuỳ nhu cầu
        hashes = [center_hash] + self._get_neighbors(center_hash)
        tasks = [self._query_geohash_range(h) for h in hashes]
        query_results = await asyncio.gather(*tasks)

        hotels = []

        seen_ids = set()
        for docs in query_results:
            for doc in docs:
                if doc.id in seen_ids:  # skip repeated document
                    continue

                seen_ids.add(doc.id)

                data = doc.to_dict()
                try:
                    hotel = DiscoverHotel.model_validate(data)
                    hotels.append(hotel)
                except Exception as e:
                    logger.error(
                        f"Error validating hotel data for document {doc.id}: {str(e)}"
                    )

        return hotels

    async def get_hotels(self, property_tokens: list[str]) -> dict[str, HotelDocument]:
        """Lấy thông tin nhiều khách sạn từ danh sách property tokens.

        Raises:
            ValidationError: Nếu property_tokens rỗng hoặc lỗi trong quá trình truy vấn
        """
        if not property_tokens:
            raise ValidationError("No property tokens provided")

        try:
            doc_refs = [self._collection.document(token) for token in property_tokens]
            docs = [doc async for doc in self._db.get_all(doc_refs)]
            hotels = {}
            for doc in docs:
                if not doc.exists:
                    continue

                data = doc.to_dict() or {}
                data["id"] = doc.id
                try:
                    hotel = HotelDocument.model_validate(data)
                    hotels[doc.id] = hotel
                except PydanticValidationError as e:
                    logger.error(
                        f"Error validating hotel data for document {doc.id}: {str(e)}"
                    )

        except Exception as e:
            logger.error(f"Error fetching hotels: {str(e)}")
            hotels = {}
        return hotels

    async def get_places(self, place_ids: list[str]) -> list[HotelDocument]:
        """Lấy thông tin nhiều địa điểm (places) dựa trên place_ids.

        Raises:
            ValidationError: Nếu place_ids rỗng hoặc lỗi trong quá trình truy vấn
        """
        hotel_data = await self.get_hotels(place_ids)

        return [hotel_data[pid] for pid in place_ids if pid in hotel_data]

    async def valid_ids(self, place_ids: list[str]) -> list[str]:
        """Kiểm tra xem tất cả place_ids có tồn tại trong database hay không.

        Raises:
            ValidationError: Nếu place_ids rỗng
        """

        if not place_ids:
            raise ValidationError("No place IDs provided for validation")

        return [
            doc.id
            async for doc in self._db.get_all(
                [self._collection.document(pid) for pid in place_ids]
            )
            if doc.exists
        ]


hotel_repo = HotelRepository()
