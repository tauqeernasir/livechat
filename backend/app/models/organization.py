"""Organization model."""

from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class Organization(BaseModel, table=True):
    """Organization model for storing business profile.

    Attributes:
        id: The primary key
        name: Name of the organization
        website_url: Optional website URL
        industry: Optional industry
        logo_path: Optional path to logo image
        primary_color: Primary brand color (hex)
        created_at: When the organization was created
        users: Relationship to organization's users
        workspaces: Relationship to organization's workspaces
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    website: Optional[str] = Field(default=None)
    industry: Optional[str] = Field(default=None)
    logo_path: Optional[str] = Field(default=None)
    primary_color: str = Field(default="#4f46e5")

    users: List["User"] = Relationship(back_populates="organization")
    workspaces: List["Workspace"] = Relationship(back_populates="organization")
