from core.exceptions import *
from externals.SerpAPI import serp_api
from externals.Gemini import gemini_client
from core.database import firebase_manager
import time

class HealthService:
    def __init__(self):
        self.start_time = time.time()

    def info(self) -> dict:
        return {
                "start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time)),
                "up_time": time.strftime("%H:%M:%S", time.gmtime(time.time() - self.start_time)),
                "serp_api": serp_api.get_status(),
                "gemini_api": gemini_client.get_status(),
                "database": firebase_manager.get_status()
            }


healthService = HealthService()