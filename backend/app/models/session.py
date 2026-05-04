"""This file contains the session model for the application."""

from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)

from sqlmodel import (
    Field,
    Relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class Session(BaseModel, table=True):
    """Session model for storing chat sessions.

    Attributes:
        id: The primary key
        user_id: Foreign key to the user (nullable for anonymous widget sessions)
        workspace_id: Foreign key to the workspace
        name: Name of the session (defaults to empty string)
        username: Display name copied from the user at session creation
        source: Origin of the session ("dashboard" or "widget")
        created_at: When the session was created
        user: Relationship to the session owner
        workspace: Relationship to the workspace
    """

    id: str = Field(primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    name: str = Field(default="")
    username: Optional[str] = Field(default=None)
    source: str = Field(default="dashboard")

    user: Optional["User"] = Relationship(back_populates="sessions")
    workspace: "Workspace" = Relationship(back_populates="sessions")
