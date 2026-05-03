"""Agent configuration models."""

from datetime import datetime, UTC
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, Column
from sqlalchemy import Text
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class AgentConfiguration(BaseModel, table=True):
    """Configuration for a chatbot agent in a workspace.

    Attributes:
        id: Primary key
        workspace_id: Foreign key to workspace (unique)
        persona: AI agent persona instructions
        fallback_rule: Instructions for unknown queries
        updated_at: When the configuration was last updated
        workspace: Relationship to workspace
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True, unique=True)
    persona: str = Field(
        default="You are a helpful and polite AI customer support assistant.",
        sa_column=Column(Text)
    )
    fallback_rule: str = Field(
        default="If you don't know the answer, politely ask the user to provide their email so a human can follow up.",
        sa_column=Column(Text)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)}
    )

    workspace: "Workspace" = Relationship(back_populates="agent_config")
