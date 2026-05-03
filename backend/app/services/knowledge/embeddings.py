"""Embedding service for generating vector representations."""

from abc import ABC, abstractmethod
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from app.core.config import settings


class BaseEmbeddingService(ABC):
    """Abstract base class for embedding generation."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of text strings."""
        pass


class SentenceTransformerEmbeddingService(BaseEmbeddingService):
    """Local embedding service using SentenceTransformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize with a specific model.
        
        Default: all-MiniLM-L6-v2 (384 dimensions, fast and efficient).
        """
        self.model = SentenceTransformer(model_name)

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        embedding = self.model.encode(text)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        embeddings = self.model.encode(texts)
        return embeddings.tolist()


# Factory or Singleton for the embedding service
class EmbeddingServiceFactory:
    """Factory to provide the configured embedding service."""

    _instance: Optional[BaseEmbeddingService] = None

    @classmethod
    def get_service(cls) -> BaseEmbeddingService:
        """Get the singleton instance of the configured embedding service."""
        if cls._instance is None:
            # In the future, this can check settings to return OpenAI, etc.
            cls._instance = SentenceTransformerEmbeddingService()
        return cls._instance
