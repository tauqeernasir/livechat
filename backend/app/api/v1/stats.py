"""Overview stats API endpoint."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.v1.auth import get_current_user
from app.models.integration import Integration
from app.models.knowledge import KnowledgeSource
from app.models.lead import Lead
from app.models.session import Session
from app.models.user import User
from app.services.database import database_service

router = APIRouter()


@router.get("/overview")
async def get_overview_stats(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Get overview stats for the dashboard."""
    total_chats = (
        await session.execute(
            select(func.count(Session.id)).where(
                Session.workspace_id == workspace_id
            )
        )
    ).scalar_one()

    leads_captured = (
        await session.execute(
            select(func.count(Lead.id)).where(Lead.workspace_id == workspace_id)
        )
    ).scalar_one()

    knowledge_docs = (
        await session.execute(
            select(func.count(KnowledgeSource.id)).where(
                KnowledgeSource.workspace_id == workspace_id
            )
        )
    ).scalar_one()

    integrations_count = (
        await session.execute(
            select(func.count(Integration.id)).where(
                Integration.workspace_id == workspace_id
            )
        )
    ).scalar_one()

    return {
        "total_chats": total_chats,
        "leads_captured": leads_captured,
        "knowledge_docs": knowledge_docs,
        "integrations": integrations_count,
    }
