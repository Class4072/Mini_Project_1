import asyncio
import threading
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.core.logger import app_logger


class EmbeddingService:
    _instance = None
    _model = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance

    def initialize(self):
        """Lazy load the sentence transformer model with thread safety."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    app_logger.info(
                        f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME} on device: {settings.EMBEDDING_DEVICE}"
                    )
                    self._model = SentenceTransformer(
                        model_name_or_path=settings.EMBEDDING_MODEL_NAME,
                        device=settings.EMBEDDING_DEVICE,
                    )
                    app_logger.info("Embedding model loaded successfully.")

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self.initialize()
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single text (동기 방식)."""
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Text cannot be empty for embedding generation.")
        
        vector = self.model.encode(
            cleaned_text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector.tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embedding vectors for a batch of texts (동기 방식)."""
        if not texts:
            return []
        
        vectors = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    async def embed_text_async(self, text: str) -> List[float]:
        """FastAPI 이벤트 루프 블로킹을 방지하기 위해 CPU 딥러닝 연산을 별도 스레드 풀에 위임."""
        return await asyncio.to_thread(self.embed_text, text)

    async def embed_batch_async(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """배치 임베딩 연산을 별도 스레드 풀에 위임하여 비동기 실행."""
        return await asyncio.to_thread(self.embed_batch, texts, batch_size)


embedding_service = EmbeddingService()
