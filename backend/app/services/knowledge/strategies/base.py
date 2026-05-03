"""Base classes for knowledge processing strategies."""

from abc import ABC, abstractmethod
from typing import List


class BaseExtractor(ABC):
    """Abstract base class for text extraction strategies."""

    @abstractmethod
    def extract(self, content: bytes) -> str:
        """Extract text from the given raw content.

        Args:
            content: Raw bytes of the document.

        Returns:
            str: Extracted text.
        """
        pass


class BaseChunker(ABC):
    """Abstract base class for text chunking strategies."""

    @abstractmethod
    def chunk(self, text: str) -> List[str]:
        """Split text into granular chunks.

        Args:
            text: Full text content.

        Returns:
            List[str]: List of text chunks.
        """
        pass
