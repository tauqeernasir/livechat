"""Chunking strategies using LangChain splitters."""

from typing import List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.knowledge.strategies.base import BaseChunker


class RecursiveChunker(BaseChunker):
    """Standard recursive character text splitter.
    
    This strategy tries to split on paragraphs, then sentences, then words.
    """

    def __init__(
        self, 
        chunk_size: int = 500, 
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None
    ):
        """Initialize the chunker with specific parameters."""
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators or ["\n\n", "\n", ".", " ", ""]
        )

    def chunk(self, text: str) -> List[str]:
        """Split text into chunks."""
        return self.splitter.split_text(text)
