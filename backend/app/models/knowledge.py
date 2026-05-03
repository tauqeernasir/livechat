"""Knowledge management models."""

from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, JSON, Column
from sqlalchemy import String, Text
from pgvector.sqlalchemy import Vector
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class SourceType(str, Enum):
    """Types of knowledge sources."""

    FILE = "file"
    MANUAL = "manual"


class SourceStatus(str, Enum):
    """Processing status of a knowledge source."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class KnowledgeSource(BaseModel, table=True):
    """Knowledge source model for a workspace.

    Attributes:
        id: Primary key
        workspace_id: Foreign key to workspace
        source_type: Type of source (file, manual)
        name: Name of the source
        content: Extracted or manual text content
        file_key: S3 key for uploaded files
        status: Current processing status
        error_message: Error message if processing failed
        chunks: Relationship to document chunks
        workspace: Relationship to workspace
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    source_type: SourceType = Field(sa_column=Column(String))
    name: str = Field(index=True)
    content: Optional[str] = Field(default=None, sa_column=Column(Text))
    file_key: Optional[str] = Field(default=None, index=True)
    status: SourceStatus = Field(default=SourceStatus.PENDING, sa_column=Column(String))
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))

    workspace: "Workspace" = Relationship(back_populates="knowledge_sources")
    chunks: List["DocumentChunk"] = Relationship(back_populates="source", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class DocumentChunk(BaseModel, table=True):
    """Granular chunk of text from a knowledge source with its embedding.

    Attributes:
        id: Primary key
        source_id: Foreign key to knowledge source
        text: The text content of the chunk
        vector: Vector embedding of the text (384 dimensions for all-MiniLM-L6-v2)
        metadata: Additional metadata for the chunk
        source: Relationship to knowledge source
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="knowledgesource.id", index=True)
    text: str = Field(sa_column=Column(Text))
    # Using 384 dimensions as default for all-MiniLM-L6-v2
    vector: Optional[List[float]] = Field(default=None, sa_column=Column(Vector(384)))
    chunk_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))

    source: KnowledgeSource = Relationship(back_populates="chunks")
