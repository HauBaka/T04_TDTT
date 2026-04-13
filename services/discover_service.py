from core.exceptions import *
from schemas.discover_schema import DiscoverRequest, DiscoverHotel
from externals.SerpAPI import serp_api
from core.database import get_db
from google.cloud import firestore

class DiscoverService:
    def __init__(self, payload: DiscoverRequest):
        self.payload = payload

    async def raw_search(self) -> list[DiscoverHotel]:
        """Gọi SerpAPI để lấy dữ liệu thô dựa trên payload đầu vào"""
        hotel_list = []
        token = None
        data = serp_api.search_places(
            query=self.payload.address,
            language=self.payload.language,
            check_in_date=self.payload.check_in.strftime("%Y-%m-%d"),
            check_out_date=self.payload.check_out.strftime("%Y-%m-%d"),
            adults=self.payload.adults,
            children=self.payload.children,
            min_price=self.payload.min_price,
            max_price=self.payload.max_price,
        )
        results = data.get("results", [])

        for hotel in results:
            hotel["address"] = hotel.get("address", "") or self.payload.address
            hotel["price"] = (hotel.get("rate_per_night") or {}).get("extracted_lowest", 0)
            hotel["property_type"] = hotel.get("type", "")
            hotel["raw_rating"] = hotel.get("overall_rating", 0.0)
            hotel["trust_weight"] = 0.0
            hotel["ai_score"] = 0.0
            hotel["ai_overview"] = None
            hotel["ai_summary"] = None
            hotel["ai_score_expiration_date"] = None
            hotel["ai_summary_expiration_date"] = None
            try:
                hotel_list.append(DiscoverHotel(**hotel))
            except Exception as e:
                print(f"Error parsing hotel data: {str(e)} - Data: {hotel}")

        return hotel_list
    async def hard_filter(self, raw_data: list[DiscoverHotel]) -> list[DiscoverHotel]:
        """Lọc dữ liệu thô theo các tiêu chí cứng"""
        return raw_data

    async def execute_discover_pipeline(self, payload: DiscoverRequest) -> list[DiscoverHotel]:
        """Thực thi pipeline tìm kiếm"""
        raw_results = await self.raw_search()
        filtered_results = await self.hard_filter(raw_results)
        # ...
        db = get_db()
        batch = db.batch()
        
        for hotel in filtered_results:
            doc_id = hotel.property_token
            if doc_id:
                doc_ref = db.collection("hotels").document(doc_id)
                hotel_data = hotel.dict()
                hotel_data.update({
                    "search_address": payload.address,
                    "update_at": firestore.SERVER_TIMESTAMP,
                    "status": "raw"
                })
                batch.set(doc_ref, hotel_data, merge=True)
        batch.commit()
        return filtered_results