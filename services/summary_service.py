import json
import logging
import re
import asyncio
from externals.Gemini import gemini_client
from services.weather_service import WeatherService
from schemas.discover_schema import AnalyzedReview, NearbyPlace, AIReviewSummary, WeatherInfo
import textwrap
logger = logging.getLogger(__name__)

class SummaryService:
    def __init__(self):
        self.ai_client = gemini_client
        self.weather_service = WeatherService()

    async def generate_places_summary(
                self, 
                analyzed_reviews: list[AnalyzedReview], 
                hotel_name: str,
                amenities: list[str] = [],
                nearby_places: list[NearbyPlace] = [],
                weather: list[WeatherInfo] = None
            ) -> AIReviewSummary:
        
        """
        Multi-source RAG: Tóm tắt dựa trên Reviews, Tiện ích, Thời tiết và Vị trí.
        """
        # Lọc & Sắp xếp Reviews (Retrieval)
        # Chỉ lấy review có độ tin cậy > 0.5
        valid_reviews = [rev for rev in analyzed_reviews if rev.trust_weight > 0.5]
        
        # Sắp xếp theo Trust Weight giảm dần (Lấy những review uy tín nhất lên đầu)
        valid_reviews.sort(key=lambda x: x.trust_weight, reverse=True)
                 
        # Chỉ lấy text của top 5 review xịn nhất để tiết kiệm Token
        trusted_texts = [rev.text for rev in valid_reviews[:5]]
        # Nếu không có review nào đủ tin cậy, vẫn phải đảm bảo context_reviews có giá trị để prompt không bị lỗi
        context_reviews = "\n- ".join(trusted_texts) if trusted_texts else "Chưa có đánh giá chi tiết."

        # Xử lý amenities và nearby_places để đưa vào prompt
        context_amenities = ", ".join(amenities) if amenities else "Không có dữ liệu tiện ích."
        
        # Xử lý nearby_places theo đúng cấu trúc có chứa 'transportations'
        context_nearby_list = []
        if nearby_places:
            for p in nearby_places:
                name = p.name
                transportations = getattr(p, "transportations", [])
                
                if transportations:
                    # Lấy thông tin di chuyển đầu tiên (ví dụ: Walking - 4 phút)
                    trans = transportations[0]
                    trans_type = getattr(trans, "type", "Đi lại")
                    duration = getattr(trans, "duration", "Không rõ")
                    # Thêm vào context với định dạng: "Tên địa điểm (Phương tiện: Thời gian)"
                    context_nearby_list.append(f"{name} ({trans_type}: {duration})")
                else:
                    context_nearby_list.append(name)
            
            context_nearby = "\n- ".join(context_nearby_list)
        else:
            context_nearby = "Không có dữ liệu vị trí."
        
        # Xử lý weather để đưa vào prompt
        if weather:
            context_weather= await self.weather_service.summarize_trip_weather(weather)
        else:
            context_weather="Chưa có dữ liệu thời tiết."

        # 3. Xây dựng prompt
        prompt = textwrap.dedent(f"""
        Bạn là một Chuyên gia Đánh giá Khách sạn độc lập. Nhiệm vụ của bạn là tổng hợp cái nhìn khách quan nhất về khách sạn "{hotel_name}" dựa trên 3 nguồn dữ liệu dưới đây.

        [RÀNG BUỘC PHÂN TÍCH - TUYỆT ĐỐI TUÂN THỦ]:
        1. TỔNG HỢP ĐA CHIỀU: Ghép nối khéo léo Đánh giá + Tiện ích + Thời tiết + Vị trí. (VD: "Phòng hơi nhỏ nhưng bù lại vị trí đắc địa, chỉ mất 4 phút đi bộ ra Chùa Ngọc Hoàng").
        2. TƯ VẤN THỜI TIẾT: Dựa trên dự báo chuyến đi, hãy đưa ra lời khuyên thực tế (Ưu tiên tiện ích trong nhà nếu mưa; Ưu tiên hồ bơi/biển nếu nắng nóng).
        3. XỬ LÝ MÂU THUẪN: Nếu khách khen chê trái chiều về cùng 1 vấn đề, hãy dùng từ ngữ trung lập (VD: "Có ý kiến trái chiều về thái độ nhân viên").
        4. HIỂU TỪ LÓNG (Slang): Tự động dịch các từ lóng mạng Việt Nam (xịn xò, chê mạnh, dơ, okela...) thành ngữ nghĩa chuẩn.
        5. ZERO HALLUCINATION: Bắt buộc chỉ dùng dữ liệu được cung cấp. Nếu dữ liệu quá ít, hãy điền: "Chưa có đủ thông tin".

        [RÀNG BUỘC ĐẦU RA - QUAN TRỌNG NHẤT]:
        - Bạn là một API Backend.
        - Trả về ĐÚNG MỘT ĐỐI TƯỢNG JSON thuần túy.
        - KHÔNG dùng dấu markdown (cấm dùng ```json hay ```).
        - KHÔNG thêm bất kỳ câu chào hỏi hay giải thích nào (cấm nói "Dạ đây là...", "Tuy nhiên...").
        - Ký tự đầu tiên phải là `{{` và ký tự cuối cùng phải là `}}`.

        Cấu trúc JSON đầu ra:
        {{
            "overview": "Viết 1 đoạn văn ngắn (2-3 câu) tóm tắt tổng quan nhất về chất lượng, vị trí, thời tiết và trải nghiệm tại khách sạn này.",
            "pros": ["Ưu điểm 1", "Ưu điểm 2"],
            "cons": ["Nhược điểm 1", "Nhược điểm 2"],
            "notes": "1 câu tóm tắt vibe chung, phốt (nếu có), cảnh báo thời tiết hoặc lời khuyên chân thành cho người sắp đặt phòng."
        }}

        --- DỮ LIỆU ĐẦU VÀO ---
        [1. ĐÁNH GIÁ THỰC TẾ]:
        {context_reviews}

        [2. TIỆN ÍCH KHÁCH SẠN]:
        {context_amenities}

        [3. ĐỊA ĐIỂM LÂN CẬN (Khoảng cách)]:
        {context_nearby}
        
        [4. DỰ BÁO THỜI TIẾT TẠI ĐIỂM ĐẾN]:
        {context_weather}
        """
        )

        # Gọi Gemini
        try:
            response_text = await asyncio.to_thread(self.ai_client.generate_content, prompt)
            if not response_text:
                raise ValueError("Gemini API trả về rỗng.")

            # Trích xuất JSON từ phản hồi
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                json_string = match.group(0)
                try:
                    summary_data = json.loads(json_string)
                    return AIReviewSummary(**summary_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Lỗi cú pháp JSON từ Gemini: {e}")
                    raise ValueError("AI sinh cấu trúc lỗi.")
            else:
                raise ValueError("Không tìm thấy JSON.")
            
        except Exception as e:
            logger.error(f"Lỗi AI Summary cho '{hotel_name}': {str(e)}")
            return AIReviewSummary(
                overview= "Không thể tải tóm tắt tổng quan lúc này.",
                pros= ["Không thể tải tóm tắt ưu điểm lúc này."],
                cons= ["Không thể tải tóm tắt nhược điểm lúc này."],
                notes= "Hệ thống AI đang bận, vui lòng thử lại sau."
            )