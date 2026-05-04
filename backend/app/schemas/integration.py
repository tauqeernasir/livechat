"""Schemas for integration API requests and responses."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class IntegrationCreate(BaseModel):
    """Create an integration from an OpenAPI spec."""

    name: str = Field(..., min_length=1, max_length=255)
    spec_url: Optional[str] = Field(
        default=None,
        max_length=2048,
        description="URL to fetch the OpenAPI spec from. Mutually exclusive with spec_content.",
    )
    spec_content: Optional[dict] = Field(
        default=None,
        description="Raw OpenAPI spec as JSON. Mutually exclusive with spec_url.",
    )
    auth_type: str = Field(
        default="none",
        pattern=r"^(none|bearer|api_key|header)$",
        description="Authentication type for the external API.",
    )
    auth_header_name: str = Field(
        default="Authorization",
        max_length=255,
    )
    credentials: Optional[str] = Field(
        default=None,
        max_length=4096,
        description="API key or bearer token value. Will be encrypted at rest.",
    )
    base_url: Optional[str] = Field(
        default=None,
        max_length=2048,
        description="Override the base URL from the spec.",
    )


class IntegrationUpdate(BaseModel):
    """Partial update for an integration."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    auth_type: Optional[str] = Field(default=None, pattern=r"^(none|bearer|api_key|header)$")
    auth_header_name: Optional[str] = Field(default=None, max_length=255)
    credentials: Optional[str] = Field(default=None, max_length=4096)
    base_url: Optional[str] = Field(default=None, max_length=2048)
    enabled: Optional[bool] = None


class OperationToggle(BaseModel):
    """Enable or disable specific operations."""

    operation_ids: List[int] = Field(..., min_length=1)
    enabled: bool


class OperationResponse(BaseModel):
    """Response schema for an integration operation."""

    id: int
    operation_id: str
    method: str
    path: str
    summary: Optional[str] = None
    description: Optional[str] = None
    enabled: bool

    model_config = {"from_attributes": True}


class IntegrationResponse(BaseModel):
    """Response schema for an integration."""

    id: int
    workspace_id: int
    name: str
    integration_type: str
    spec_url: Optional[str] = None
    auth_type: str
    base_url: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    enabled: bool
    created_at: datetime
    updated_at: datetime
    operations: List[OperationResponse] = []

    model_config = {"from_attributes": True}


class IntegrationListResponse(BaseModel):
    """Response schema for listing integrations."""

    integrations: List[IntegrationResponse]


class IntegrationSyncResponse(BaseModel):
    """Response after triggering a spec sync."""

    integration_id: int
    status: str
    message: str
