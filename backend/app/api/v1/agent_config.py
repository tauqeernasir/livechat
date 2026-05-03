"""Agent configuration API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.models.agent_config import AgentConfiguration
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.services.database import database_service
from app.core.logging import logger
from pydantic import BaseModel

router = APIRouter()


class AgentConfigUpdate(BaseModel):
    """Schema for updating agent configuration."""
    persona: Optional[str] = None
    fallback_rule: Optional[str] = None


@router.get("/{workspace_id}")
async def get_agent_config(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Get the agent configuration for a workspace."""
    statement = select(AgentConfiguration).where(AgentConfiguration.workspace_id == workspace_id)
    result = await session.execute(statement)
    config = result.scalar_one_or_none()
    
    if not config:
        # Create a default config if it doesn't exist
        config = AgentConfiguration(workspace_id=workspace_id)
        session.add(config)
        await session.commit()
        await session.refresh(config)
        
    return config


@router.patch("/{workspace_id}")
async def update_agent_config(
    workspace_id: int,
    config_update: AgentConfigUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Update the agent configuration for a workspace."""
    statement = select(AgentConfiguration).where(AgentConfiguration.workspace_id == workspace_id)
    result = await session.execute(statement)
    config = result.scalar_one_or_none()
    
    if not config:
        config = AgentConfiguration(workspace_id=workspace_id)
    
    if config_update.persona is not None:
        config.persona = config_update.persona
    if config_update.fallback_rule is not None:
        config.fallback_rule = config_update.fallback_rule
        
    session.add(config)
    await session.commit()
    await session.refresh(config)
    
    logger.info("agent_config_updated", workspace_id=workspace_id)
    return config
