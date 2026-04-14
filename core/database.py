import firebase_admin
from firebase_admin import credentials, firestore_async
from core.settings import settings
import os

class FirebaseManager:
    def __init__(self):
        self._db = None

    def initialize(self):
        if not firebase_admin._apps:
            if not os.path.exists(settings.FIREBASE_CREDENTIAL):
                raise FileNotFoundError(f"File not found: {settings.FIREBASE_CREDENTIAL}.")
                
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIAL)
            firebase_admin.initialize_app(cred)
            
        self._db = firestore_async.client()

    def get_db(self):
        if self._db is None:
            raise RuntimeError("Database not initialized.")
        return self._db

    async def get_status(self) -> str:
        if self._db is None:
            return "disconnected"
        try:
            await self._db.collection("dummy").document("ping").get()
            return "connected"
        except Exception as e:
            return f"error: {str(e)}"

firebase_manager = FirebaseManager()
get_db = firebase_manager.get_db