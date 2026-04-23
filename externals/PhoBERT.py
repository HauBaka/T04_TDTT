from __future__ import annotations

from loguru import logger
from transformers import pipeline


class PhoBERTClient:
    def __init__(self, model_name: str = "wonrax/phobert-base-vietnamese-sentiment"):
        self.model_name = model_name
        self._pipeline = None

    def _ensure_loaded(self) -> None:
        if self._pipeline is not None:
            return

        try:
            self._pipeline = pipeline(
                "sentiment-analysis",  # type: ignore
                model=self.model_name,
                device=-1,
            )
            logger.info(f"PhoBERT ready: {self.model_name}")
        except Exception as exc:
            self._pipeline = None
            logger.warning(f"Không tải được PhoBERT '{self.model_name}': {str(exc)}")

    def __call__(self, texts):
        self._ensure_loaded()
        if self._pipeline is None:
            raise RuntimeError("PhoBERT is not available")
        return self._pipeline(texts)


PhoBERT = PhoBERTClient()

