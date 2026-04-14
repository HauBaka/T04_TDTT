from google import genai
from google.genai import errors
from loguru import logger
from utils.beauty_json import beauty_json
from core.settings import settings

class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.default_model = 'gemini-2.5-flash'

    def generate_content(self, prompt: str) -> str | None:
        try:
            response = self.client.models.generate_content(
                model=self.default_model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            raise Exception(f"Error calling Gemini API: {str(e)}")

    def get_status(self) -> dict:
        try:
            model_info = self.client.models.get(model=self.default_model)
            return {
                "model_name": self.default_model,
                "content": "connected" if  model_info and hasattr(model_info, 'name') else "not available"
            }
        except Exception as e:
            logger.error(beauty_json({"Error checking Gemini API status": getattr(e, 'message', str(e))}))
            return {
                "model_name": self.default_model,
                "content": "Not available"
            }

gemini_client = GeminiClient()