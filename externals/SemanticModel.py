from __future__ import annotations

from loguru import logger
from transformers import AutoModel, AutoTokenizer


class SemanticModelClient:
	def __init__(self, model_name: str = "intfloat/multilingual-e5-small"):
		self.model_name = model_name
		self._tokenizer = None
		self._model = None
		self._available: bool | None = None

	def _ensure_loaded(self) -> None:
		if self._available is not None:
			return

		try:
			self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
			self._model = AutoModel.from_pretrained(self.model_name)
			self._model.eval()
			self._available = True
			logger.info(f"Semantic model ready: {self.model_name}")
		except Exception as exc:
			self._available = False
			self._tokenizer = None
			self._model = None
			logger.warning(f"Không tải được semantic model '{self.model_name}': {str(exc)}")

	@property
	def tokenizer(self):
		self._ensure_loaded()
		return self._tokenizer

	@property
	def semantic_model(self):
		self._ensure_loaded()
		return self._model


semantic_model_client = SemanticModelClient()