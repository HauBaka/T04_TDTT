import json
import re
import httpx
from loguru import logger

# phải vào termainal gõ "ollama run qwen2.5:3b" nhé sếp (máy host é)

class LocalOllamaClient:
    def __init__(self):
        # Địa chỉ mặc định khi cài Ollama trên máy
        self._url = "http://localhost:11434/api/generate"
        
        # Đổi thành "qwen2.5:7b" nếu muốn thông minh hơn (nhưng sẽ nặng vcl)
        self._model = "qwen2.5:3b" 
        
        self._http_client = httpx.Client(timeout=30.0)
    
    def generate_content(self, prompt: str) -> str:
        """
        Drop-in replacement cho Gemini API.
        Nhận vào Prompt -> Gọi Local GPU -> Trả về chuỗi JSON (String)
        """
        payload = {
            "model": self._model,
            "prompt": prompt,
            "system": "Bạn là một hệ thống API Backend. BẮT BUỘC phải trả về ĐÚNG MỘT ĐỐI TƯỢNG JSON thuần túy, KHÔNG có markdown, KHÔNG có text giải thích bên ngoài. Viết bằng Tiếng Việt tự nhiên.",
            "format": "json", # Local AI chỉ nhả ra cấu trúc JSON
            "stream": False,
            "options": {
                "temperature": 0.2, # Giảm độ sáng tạo để tránh model bị ảo
                "num_predict": 1024 # Giới hạn token đầu ra
            }
        }

        try:
            response = self._http_client.post(self._url, json=payload)
            response.raise_for_status() 
            
            data = response.json()
            json_string = data.get("response", "")
            
            # Parse thử để đảm bảo JSON không bị vỡ
            json.loads(json_string) 
            
            return json_string

        except httpx.ConnectError:
            logger.error("Không thể kết nối tới Ollama. Đảm bảo đã bật Ollama Server")
            return self._fallback_generate(prompt)
        except httpx.HTTPStatusError as e:
            logger.error(f"Local AI Error (Status {e.response.status_code}): {e.response.text}")
            return self._fallback_generate(prompt)
        except json.JSONDecodeError as e:
            logger.error(f"Local AI sinh JSON lỗi: {e}")
            return self._fallback_generate(prompt)
        except Exception as e:
            logger.error(f"Lỗi không xác định: {str(e)}")
            return self._fallback_generate(prompt)

    # fallback - chạy 100% trên cpu
    def _fallback_generate(self, prompt: str) -> str:
        try:
            reviews_section = self._extract_section(prompt, "[1. ĐÁNH GIÁ THỰC TẾ]")
            amenities_section = self._extract_section(prompt, "[2. TIỆN ÍCH KHÁCH SẠN]")
            nearby_section = self._extract_section(prompt, "[3. ĐỊA ĐIỂM LÂN CẬN (Khoảng cách)]")
            weather_section = self._extract_section(prompt, "[4. DỰ BÁO THỜI TIẾT TẠI ĐIỂM ĐẾN]")
            
            hotel_name = self._extract_hotel_name(prompt)
            pros, cons, notes = self._analyze_reviews(reviews_section)
            
            overview = self._generate_overview(
                hotel_name, reviews_section, amenities_section, nearby_section, weather_section
            )

            result = {
                "overview": overview,
                "pros": pros,
                "cons": cons,
                "notes": notes
            }
            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Fallback Error: {str(e)}")
            return json.dumps({
                "overview": "Hệ thống đang bảo trì, chưa thể tạo tóm tắt chi tiết.",
                "pros": ["Thông tin đang cập nhật"],
                "cons": ["Thông tin đang cập nhật"],
                "notes": "Vui lòng thử lại sau."
            }, ensure_ascii=False)

    # các hàm xử lí fallback
    def _extract_section(self, text: str, marker: str) -> str:
        try:
            start = text.find(marker)
            if start == -1: return ""
            end = text.find("[", start + len(marker))
            if end == -1: end = len(text)
            return text[start + len(marker):end].strip()
        except: return ""

    def _extract_hotel_name(self, prompt: str) -> str:
        match = re.search(r'khách sạn "([^"]+)"', prompt, re.IGNORECASE)
        return match.group(1) if match else "Khách Sạn"

    def _analyze_reviews(self, reviews_text: str) -> tuple[list[str], list[str], str]:
        if not reviews_text or "Chưa có" in reviews_text:
            return [], [], "Chưa có đủ dữ liệu đánh giá."

        text_lower = reviews_text.lower()
        positive = ['tốt', 'đẹp', 'sạch', 'thân thiện', 'tiện', 'rẻ', 'hài lòng', 'tuyệt', 'yên tĩnh']
        negative = ['xấu', 'bẩn', 'hỏng', 'kém', 'xa', 'đắt', 'tệ', 'dơ', 'ồn', 'thất vọng']

        pros = [f"{k.capitalize()}" for k in positive if k in text_lower][:3]
        cons = [f"{k.capitalize()}" for k in negative if k in text_lower][:3]

        sentences = [s.strip() for s in reviews_text.split('.') if len(s.strip()) > 10]
        notes = sentences[0][:100] if sentences else "Khách hàng có trải nghiệm khá tốt."
        return pros, cons, notes

    def _generate_overview(self, hotel_name: str, reviews: str, amenities: str, nearby: str, weather: str) -> str:
        parts = [f"{hotel_name}"]
        if "Chưa có" not in reviews: parts.append("có đánh giá tích cực")
        if amenities and "Không có" not in amenities:
            a_list = [a.strip() for a in amenities.split(',') if a.strip()][:2]
            if a_list: parts.append(f"có {', '.join(a_list)}")
        
        weather_note = ""
        if "mưa" in weather.lower(): weather_note = " Dự báo có mưa, nên lưu ý lịch trình."
        elif "nắng" in weather.lower() or "nóng" in weather.lower(): weather_note = " Thời tiết nắng đẹp."

        return " ".join(parts) + "." + weather_note
    
    def close(self):
        """Hàm dọn dẹp kết nối khi tắt app"""
        self._http_client.close()

ollama_client = LocalOllamaClient()