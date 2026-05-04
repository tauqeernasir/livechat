"""Schemas for widget API endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


class WidgetSessionResponse(BaseModel):
    """Response from widget session creation."""

    session_id: str
    access_token: str
    expires_at: datetime


class WidgetConfigPublicResponse(BaseModel):
    """Public widget configuration returned to the embed script."""

    position: str
    primary_color: str
    welcome_message: str
    placeholder_text: str
    icon_url: Optional[str] = None
    lead_capture_enabled: bool
    lead_capture_fields: list[str]
    allowed_origins: list[str] = []


class WidgetConfigAdminResponse(BaseModel):
    """Full widget configuration for dashboard admin."""

    id: int
    workspace_id: int
    widget_key: str
    is_active: bool
    allowed_origins: list[str]
    position: str
    primary_color: str
    welcome_message: str
    placeholder_text: str
    icon_url: Optional[str] = None
    lead_capture_enabled: bool
    lead_capture_fields: list[str]
    updated_at: datetime


class WidgetConfigUpdateRequest(BaseModel):
    """Request to update widget configuration."""

    position: Optional[str] = None
    primary_color: Optional[str] = None
    welcome_message: Optional[str] = None
    placeholder_text: Optional[str] = None
    icon_url: Optional[str] = None
    allowed_origins: Optional[list[str]] = None
    lead_capture_enabled: Optional[bool] = None
    lead_capture_fields: Optional[list[str]] = None


class WidgetMessageResponse(BaseModel):
    """A single message in widget chat history."""

    role: str
    content: str


class LeadCreateRequest(BaseModel):
    """Request to create a lead from the widget."""

    email: str = Field(..., max_length=255)
    name: Optional[str] = Field(default=None, max_length=100)
    metadata: dict = Field(default_factory=dict)


class LeadResponse(BaseModel):
    """A lead record for the dashboard."""

    id: int
    workspace_id: int
    session_id: Optional[str] = None
    email: str
    name: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
