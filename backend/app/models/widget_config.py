"""Widget configuration model for embeddable chat widget."""

from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship

from app.models.base import BaseModel

if True:  # TYPE_CHECKING workaround for circular imports
    from app.models.workspace import Workspace


class WidgetConfig(BaseModel, table=True):
    """Widget configuration for a workspace's embeddable chat widget.

    Attributes:
        id: Primary key
        workspace_id: FK to workspace (unique — one config per workspace)
        widget_key: Publishable key (wk_ prefix) for identifying the widget
        is_active: Master toggle for enabling/disabling the widget
        allowed_origins: Optional list of allowed CORS origins
        position: Widget position on the page
        primary_color: Brand color for the widget
        welcome_message: Initial greeting shown to visitors
        placeholder_text: Input placeholder text
        icon_url: Optional custom launcher icon URL
        lead_capture_enabled: Whether lead capture form is shown before chat
        lead_capture_fields: Fields to collect in lead capture form
        updated_at: Last update timestamp
    """

    __tablename__ = "widget_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", unique=True, index=True)
    widget_key: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)
    allowed_origins: list[str] = Field(default=[], sa_column=Column(JSONB, nullable=False, server_default="[]"))
    position: str = Field(default="bottom-right")
    primary_color: str = Field(default="#6366f1")
    welcome_message: str = Field(default="Hi! How can I help you today?")
    placeholder_text: str = Field(default="Type your message...")
    icon_url: Optional[str] = Field(default=None)
    lead_capture_enabled: bool = Field(default=False)
    lead_capture_fields: list[str] = Field(
        default=["email"], sa_column=Column(JSONB, nullable=False, server_default='["email"]')
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    workspace: "Workspace" = Relationship(back_populates="widget_config")
