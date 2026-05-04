"""Lead model for widget lead capture."""

from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship

from app.models.base import BaseModel

if True:  # TYPE_CHECKING workaround
    from app.models.workspace import Workspace


class Lead(BaseModel, table=True):
    """Lead captured from the widget.

    Attributes:
        id: Primary key
        workspace_id: FK to workspace
        session_id: FK to the widget session (nullable)
        email: Lead's email address
        name: Lead's name (optional)
        metadata: Additional fields captured
        created_at: When the lead was captured
    """

    __tablename__ = "lead"

    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    session_id: Optional[str] = Field(default=None, foreign_key="session.id", nullable=True)
    email: str = Field(max_length=255)
    name: Optional[str] = Field(default=None, max_length=100)
    metadata_: dict = Field(default={}, sa_column=Column("metadata", JSONB, nullable=False, server_default="{}"))
    
    workspace: "Workspace" = Relationship()
