from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance

    def initialize(self):
        """Lazy load the sentence transformer model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME} on device: {settings.EMBEDDING_DEVICE}")
            self._model = SentenceTransformer(
                model_name_or_path=settings.EMBEDDING_MODEL_NAME,
                device=settings.EMBEDDING_DEVICE,
            )
            logger.info("Embedding model loaded successfully.")

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self.initialize()
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single text."""
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
        """Generate embedding vectors for a batch of texts."""
        if not texts:
            return []
        
        vectors = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()


embedding_service = EmbeddingService()
