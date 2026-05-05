import json
import httpx
from loguru import logger
from core.settings import settings

class GroqClient:
    def __init__(self):
        self._url = "https://api.groq.com/openai/v1/chat/completions"
        self._model = "llama-3.1-8b-instant"
        self._api_key = settings.GROQ_API_KEY
        # Giới hạn timeout Groq ở 6s để chừa đủ ngân sách cho routing và hậu xử lý
        self._http_client = httpx.Client(timeout=6.0) 
    
    def _is_json_request(self, prompt: str) -> bool:
        """Kiểm tra xem request có yêu cầu JSON output không (robust hơn)."""
        return any(keyword in prompt for keyword in ["JSON", "json_object", "Trả về", "Trả về ĐÚNG MỘT"])

    def generate_content(self, prompt: str, expect_json: bool = False) -> str:
        """
        Drop-in replacement cho Ollama API.
        Nhận vào Prompt -> Gọi Groq API -> Trả về chuỗi kết quả (String)
        
        Args:
            prompt: Nội dung prompt gửi tới Groq
            expect_json: Nếu True, ép model trả JSON và validate output
        """
        if not self._api_key:
            logger.error("Thiếu GROQ_API_KEY trong file .env")
            return self._fallback_generate(prompt)

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        # Auto-detect JSON request nếu không chỉ định rõ
        is_json_request = expect_json or self._is_json_request(prompt)
        system_msg = "Bạn là một trợ lý ảo tư vấn du lịch và khách sạn người Việt. Trả lời bằng Tiếng Việt tự nhiên."
        
        if is_json_request:
            system_msg = "Bạn là một hệ thống API Backend. BẮT BUỘC phải trả về ĐÚNG MỘT ĐỐI TƯỢNG JSON thuần túy, KHÔNG có markdown, KHÔNG có text giải thích bên ngoài. Viết bằng Tiếng Việt tự nhiên."

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,  # 0.3 tốt hơn 0.2, tự nhiên hơn nhưng vẫn consistent
        }
        
        if is_json_request:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = self._http_client.post(self._url, headers=headers, json=payload)
            response.raise_for_status() 
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Validate JSON output nếu là JSON request
            if is_json_request:
                try:
                    json.loads(content)  # Validate JSON structure
                except json.JSONDecodeError as e:
                    logger.error(f"Groq trả về JSON không hợp lệ: {e}. Content: {content[:100]}")
                    return self._fallback_generate(prompt)
            
            return content

        except httpx.ConnectError:
            logger.error("Không thể kết nối tới Groq API. Kiểm tra mạng internet.")
            return self._fallback_generate(prompt)
        except httpx.TimeoutException:
            logger.error("Groq API timeout (>6s).")
            return self._fallback_generate(prompt)
        except httpx.HTTPStatusError as e:
            logger.error(f"Groq API Error (Status {e.response.status_code}): {e.response.text}")
            return self._fallback_generate(prompt)
        except json.JSONDecodeError as e:
            logger.error(f"Lỗi parse response từ Groq: {e}")
            return self._fallback_generate(prompt)
        except KeyError as e:
            logger.error(f"Groq response format không như mong đợi: {e}")
            return self._fallback_generate(prompt)
        except Exception as e:
            logger.error(f"Lỗi không xác định: {str(e)}")
            return self._fallback_generate(prompt)

    def _fallback_generate(self, prompt: str) -> str:
        """Fallback response khi Groq API fail."""
        if self._is_json_request(prompt):
            # Trả về JSON fallback tùy theo loại request
            if "use_lodging_rag" in prompt:
                return json.dumps({
                    "intent": "casual",
                    "use_lodging_rag": False,
                    "requires_more_info": False,
                    "missing_fields": [],
                    "clarification_question": "Hệ thống AI đang bảo trì, bạn cần tôi giúp gì không?"
                }, ensure_ascii=False)
            # Fallback cho context extraction
            elif "address" in prompt and "min_price" in prompt:
                return json.dumps({
                    "address": None,
                    "min_price": 300000,
                    "max_price": 3000000,
                    "min_rating": None,
                    "required_amenities": [],
                    "adults": 2,
                    "children": None,
                    "check_in": None,
                    "check_out": None,
                    "trip_style": None,
                    "confidence": 0.0
                }, ensure_ascii=False)
            # Generic JSON fallback
            return json.dumps({"answer": "Hệ thống AI đang quá tải, vui lòng thử lại sau vài giây."}, ensure_ascii=False)
        return "Hệ thống tư vấn AI đang quá tải, vui lòng thử lại sau vài giây."

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.close()
        return False

    def close(self):
        """Close HTTP client connection."""
        self._http_client.close()

groq_client = GroqClient()
