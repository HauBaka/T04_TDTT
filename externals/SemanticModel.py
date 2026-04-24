from __future__ import annotations

from loguru import logger
from transformers import AutoModel, AutoTokenizer


class SemanticModelClient:
	def __init__(self, model_name: str = "intfloat/multilingual-e5-small"):
		self.model_name = model_name
		self._tokenizer = None
		self._model = None

	def load_model(self) -> None:
		"""Tải mô hình semantic vào bộ nhớ. Nếu đã tải rồi thì không làm gì."""
		if self._model is not None and self._tokenizer is not None:
			return

		try:
			logger.info(f"Loading semantic model '{self.model_name}'...")
			self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
			self._model = AutoModel.from_pretrained(self.model_name)
			self._model.eval()
			logger.info(f"Semantic model ready: {self.model_name}")
		except Exception as exc:
			self._tokenizer = None
			self._model = None
			raise RuntimeError(f"Failed to load semantic model: {str(exc)}")

	@property
	def tokenizer(self):
		if self._tokenizer is None:
			raise RuntimeError("Semantic model is not available")
		return self._tokenizer

	@property
	def semantic_model(self):
		if self._model is None:
			raise RuntimeError("Semantic model is not available")
		return self._model


semantic_model_client = SemanticModelClient()