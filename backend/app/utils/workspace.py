"""Workspace authorization utilities."""

from fastapi import HTTPException, status
from sqlalchemy import exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import Workspace
from app.models.user import User


async def verify_workspace_access(
    workspace_id: int,
    user: User,
    session: AsyncSession,
) -> None:
    """Verify user has access to the workspace through their organization.

    Args:
        workspace_id: The workspace to check access for.
        user: The authenticated user.
        session: Active database session.

    Raises:
        HTTPException: 403 if user has no org or workspace doesn't belong to user's org.
    """
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no organization",
        )

    result = await session.execute(
        select(
            exists().where(
                Workspace.id == workspace_id,
                Workspace.org_id == user.organization_id,
            )
        )
    )
    if not result.scalar():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace not found or unauthorized",
        )
