from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

import torch
from externals.SemanticModel import semantic_model_client

@dataclass(frozen=True)
class SemanticScore:
    # Lớp SemanticScore này để lưu trữ kết quả so sánh ngữ nghĩa giữa hai đoạn văn bản, bao gồm văn bản bên trái, văn bản bên phải, và điểm số tương đồng ngữ nghĩa được tính toán giữa chúng. Điểm số này có thể được sử dụng để đánh giá mức độ liên quan hoặc tương đồng giữa thông tin của khách sạn và sở thích hoặc hành vi của người dùng trong quá trình xếp hạng khách sạn.
    left_text: str
    right_text: str
    score: float


class SemanticTextEncoder:
    def __init__(self):
        self._tokenizer = None
        self._model = None
        self._available: bool | None = None
        self._embedding_cache: dict[str, tuple[float, ...]] = {}

    def is_available(self) -> bool:
        # Trigger lazy init and report whether model load succeeded.
        self._ensure_loaded()
        return bool(self._available)

    def encode(self, texts: list[str]) -> list[tuple[float, ...]] | None:
        self._ensure_loaded()
        if not self._available or self._tokenizer is None or self._model is None:
            return None

        normalized_texts = [text.strip() for text in texts if text and text.strip()]
        if not normalized_texts:
            return None

        # Keep original order, reuse cache when possible.
        ordered_results: list[tuple[float, ...]] = []
        missing_texts: list[str] = []
        missing_positions: list[int] = []

        for index, text in enumerate(normalized_texts):
            cached = self._embedding_cache.get(text)
            if cached is not None:
                ordered_results.append(cached)
            else:
                ordered_results.append(())
                missing_texts.append(text)
                missing_positions.append(index)

        if missing_texts:
            try:
                # Encode only uncached texts to reduce compute cost.
                encoded = self._encode_batch(missing_texts)
                for position, text, vector in zip(missing_positions, missing_texts, encoded):
                    embedding = tuple(float(value) for value in vector)
                    ordered_results[position] = embedding
                    self._embedding_cache[text] = embedding
                
                # Limit cache size to prevent memory leaks
                if len(self._embedding_cache) > 6000:
                    overflow = len(self._embedding_cache) - 6000
                    keys_to_delete = list(self._embedding_cache.keys())[:overflow]
                    for key in keys_to_delete:
                        del self._embedding_cache[key]
            except Exception as exc:
                logger.warning(f"Không thể mã hoá semantic text: {str(exc)}")
                return None

        if any(not vector for vector in ordered_results):
            return None

        return ordered_results

    def similarity(self, left_text: str, right_text: str) -> float | None:
        vectors = self.encode([left_text, right_text])
        if not vectors or len(vectors) < 2:
            return None
        return self.cosine_similarity(vectors[0], vectors[1])

    def _ensure_loaded(self) -> None:
        if self._available is not None:
            return

        try:
            # Load model/tokenizer once; all later calls reuse them.
            self._tokenizer = semantic_model_client.tokenizer
            self._model = semantic_model_client.semantic_model
            if self._model is not None:
                self._model.eval()
            self._available = self._tokenizer is not None and self._model is not None
            if self._available:
                logger.info(f"Semantic encoder ready")
            else:
                logger.warning(f"Semantic encoder not available")
        except Exception as exc:
            self._available = False
            self._tokenizer = None
            self._model = None
            logger.warning(f"Không tải được semantic encoder: {str(exc)}")

    def _encode_batch(self, texts: list[str]) -> list[torch.Tensor]:
        assert self._tokenizer is not None
        assert self._model is not None

        inputs = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )

        with torch.no_grad():
            outputs = self._model(**inputs)
            # Mean pooling over valid tokens, then L2 normalize for cosine use.
            embeddings = self._mean_pool(outputs.last_hidden_state, inputs["attention_mask"])
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        return [embedding.cpu() for embedding in embeddings]

    def _mean_pool(self, token_embeddings: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        summed = torch.sum(token_embeddings * mask, dim=1)
        counts = torch.clamp(mask.sum(dim=1), min=1e-9)
        return summed / counts

    def cosine_similarity(self, left: tuple[float, ...], right: tuple[float, ...]) -> float:
        dot = sum(a * b for a, b in zip(left, right))
        return max(-1.0, min(1.0, dot))


semantic_text_encoder = SemanticTextEncoder()
