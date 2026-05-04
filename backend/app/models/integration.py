"""Integration models for external tool connectivity."""

from datetime import datetime, UTC
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text, JSON
from sqlmodel import Column, Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class IntegrationType(str, Enum):
    """Types of external integrations."""

    OPENAPI = "openapi"
    MCP = "mcp"


class IntegrationStatus(str, Enum):
    """Sync/health status of an integration."""

    PENDING = "pending"
    SYNCING = "syncing"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


class Integration(BaseModel, table=True):
    """Workspace-scoped external integration configuration.

    Attributes:
        id: Primary key
        workspace_id: Foreign key to workspace
        name: Human-readable label for the integration
        integration_type: openapi or mcp
        spec_url: URL to fetch OpenAPI spec from (optional if spec uploaded)
        spec_content: Raw OpenAPI spec JSON stored after validation
        auth_type: Type of auth (bearer, api_key, header, none)
        auth_header_name: Header name for credential injection (default: Authorization)
        encrypted_credentials: Encrypted API key / token value
        base_url: Override base URL for API calls (optional, derived from spec)
        status: Current sync status
        error_message: Last error during sync or invocation
        enabled: Master toggle for the integration
        updated_at: Last update timestamp
        workspace: Relationship to workspace
        operations: Relationship to discovered operations
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    name: str = Field(max_length=255, index=True)
    integration_type: IntegrationType = Field(
        default=IntegrationType.OPENAPI, sa_column=Column(String)
    )

    # Spec storage
    spec_url: Optional[str] = Field(default=None, sa_column=Column(Text))
    spec_content: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Auth configuration
    auth_type: str = Field(default="none", max_length=50)
    auth_header_name: str = Field(default="Authorization", max_length=255)
    encrypted_credentials: Optional[str] = Field(
        default=None, sa_column=Column(Text)
    )

    # Runtime config
    base_url: Optional[str] = Field(default=None, sa_column=Column(Text))
    status: IntegrationStatus = Field(
        default=IntegrationStatus.PENDING, sa_column=Column(String)
    )
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    enabled: bool = Field(default=True)

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )

    workspace: "Workspace" = Relationship(back_populates="integrations")
    operations: List["IntegrationOperation"] = Relationship(
        back_populates="integration",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class IntegrationOperation(BaseModel, table=True):
    """A single callable operation derived from an integration spec.

    Attributes:
        id: Primary key
        integration_id: Foreign key to integration
        operation_id: Unique identifier within the spec (e.g. operationId)
        method: HTTP method (GET, POST, etc.)
        path: API path template
        summary: Short description for the LLM
        description: Full description for the LLM
        parameters_schema: JSON schema for the operation parameters
        response_schema: JSON schema describing the success response body
        enabled: Whether this operation is available to the model
        integration: Relationship to integration
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    integration_id: int = Field(foreign_key="integration.id", index=True)
    operation_id: str = Field(max_length=255, index=True)
    method: str = Field(max_length=10)
    path: str = Field(sa_column=Column(Text))
    summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    parameters_schema: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    response_schema: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    enabled: bool = Field(default=False)

    integration: Integration = Relationship(back_populates="operations")
