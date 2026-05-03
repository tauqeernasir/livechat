"""Extraction strategies for different file types."""

import io
from typing import List
from pypdf import PdfReader
from docx import Document
from app.services.knowledge.strategies.base import BaseExtractor


class PDFExtractor(BaseExtractor):
    """Extractor for PDF documents using pypdf."""

    def extract(self, content: bytes) -> str:
        """Extract text from PDF bytes."""
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()


class DocxExtractor(BaseExtractor):
    """Extractor for Docx documents using python-docx."""

    def extract(self, content: bytes) -> str:
        """Extract text from Docx bytes."""
        doc = Document(io.BytesIO(content))
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()


class TextExtractor(BaseExtractor):
    """Extractor for plain text or manual entries."""

    def extract(self, content: bytes) -> str:
        """Decode bytes to string."""
        try:
            return content.decode("utf-8").strip()
        except UnicodeDecodeError:
            # Fallback to latin-1 if utf-8 fails
            return content.decode("latin-1").strip()


class ExtractionRegistry:
    """Registry to map extensions to extractors."""

    _extractors = {
        "pdf": PDFExtractor(),
        "docx": DocxExtractor(),
        "txt": TextExtractor(),
    }

    @classmethod
    def get_extractor(cls, extension: str) -> BaseExtractor:
        """Get the appropriate extractor for the given extension."""
        return cls._extractors.get(extension.lower().lstrip("."), TextExtractor())
