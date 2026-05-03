"""Workspace model."""

from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.knowledge import KnowledgeSource
    from app.models.agent_config import AgentConfiguration
    from app.models.session import Session


class Workspace(BaseModel, table=True):
    """Workspace model for grouping chatbot agents.

    Attributes:
        id: The primary key
        org_id: Foreign key to the organization
        name: Name of the workspace
        is_default: Whether this is the default workspace for the organization
        timezone: Timezone for the workspace
        created_at: When the workspace was created
        organization: Relationship to the workspace's organization
        knowledge_sources: Relationship to knowledge sources
        agent_config: Relationship to agent configuration
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: int = Field(foreign_key="organization.id")
    name: str = Field(index=True)
    timezone: str = Field(default="UTC")
    is_default: bool = Field(default=False)

    organization: "Organization" = Relationship(back_populates="workspaces")
    knowledge_sources: list["KnowledgeSource"] = Relationship(
        back_populates="workspace", 
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    agent_config: Optional["AgentConfiguration"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )
    sessions: list["Session"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
