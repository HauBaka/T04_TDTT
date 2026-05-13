import os

import firebase_admin
from firebase_admin import credentials, firestore_async

from core.settings import settings


class FirebaseManager:
    def __init__(self):
        self._db = None

    async def initialize(self):
        if not firebase_admin._apps:
            firebase_credential_path = settings.FIREBASE_CREDENTIAL.get_secret_value()
            if not os.path.exists(firebase_credential_path):
                raise FileNotFoundError(f"File not found: {firebase_credential_path}.")

            cred = credentials.Certificate(firebase_credential_path)
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