"""Widget admin API endpoints for dashboard management.

These endpoints are used by business owners to configure their widget
from the dashboard. All require user authentication + workspace ownership.
"""

from datetime import datetime, UTC

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlmodel import select

from app.api.v1.auth import get_current_user
from app.core.cache import cache_service
from app.core.logging import logger
from app.models.lead import Lead
from app.models.user import User
from app.models.widget_config import WidgetConfig
from app.schemas.widget import (
    LeadResponse,
    WidgetConfigAdminResponse,
    WidgetConfigUpdateRequest,
)
from app.services.database import database_service
from app.utils.widget_keys import generate_widget_key
from app.utils.workspace import verify_workspace_access

router = APIRouter()


def _to_admin_response(config: WidgetConfig) -> WidgetConfigAdminResponse:
    return WidgetConfigAdminResponse(
        id=config.id,
        workspace_id=config.workspace_id,
        widget_key=config.widget_key,
        is_active=config.is_active,
        allowed_origins=config.allowed_origins,
        position=config.position,
        primary_color=config.primary_color,
        welcome_message=config.welcome_message,
        placeholder_text=config.placeholder_text,
        icon_url=config.icon_url,
        lead_capture_enabled=config.lead_capture_enabled,
        lead_capture_fields=config.lead_capture_fields,
        updated_at=config.updated_at,
    )


@router.get("/{workspace_id}", response_model=WidgetConfigAdminResponse)
async def get_widget_config(
    workspace_id: int,
    user: User = Depends(get_current_user),
):
    """Get widget configuration for a workspace.

    Creates a default config with a generated widget key if none exists.
    """
    async with database_service.async_session_maker() as session:
        await verify_workspace_access(workspace_id, user, session)

        stmt = select(WidgetConfig).where(WidgetConfig.workspace_id == workspace_id)
        result = await session.execute(stmt)
        config = result.scalar_one_or_none()

        if config is None:
            config = WidgetConfig(
                workspace_id=workspace_id,
                widget_key=generate_widget_key(),
            )
            session.add(config)
            await session.commit()
            await session.refresh(config)
            logger.info("widget_config_created", workspace_id=workspace_id)

        return _to_admin_response(config)


@router.patch("/{workspace_id}", response_model=WidgetConfigAdminResponse)
async def update_widget_config(
    workspace_id: int,
    update: WidgetConfigUpdateRequest,
    user: User = Depends(get_current_user),
):
    """Update widget visual settings and lead capture configuration."""
    async with database_service.async_session_maker() as session:
        await verify_workspace_access(workspace_id, user, session)

        stmt = select(WidgetConfig).where(WidgetConfig.workspace_id == workspace_id)
        result = await session.execute(stmt)
        config = result.scalar_one_or_none()

        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Widget config not found. GET the endpoint first to create a default.",
            )

        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)
        config.updated_at = datetime.now(UTC)

        session.add(config)
        await session.commit()
        await session.refresh(config)

        # Invalidate cache
        await cache_service.delete(f"widget_config:{config.widget_key}")

        logger.info("widget_config_updated", workspace_id=workspace_id, fields=list(update_data.keys()))
        return _to_admin_response(config)


@router.post("/{workspace_id}/rotate-key", response_model=WidgetConfigAdminResponse)
async def rotate_widget_key(
    workspace_id: int,
    user: User = Depends(get_current_user),
):
    """Rotate the widget key, immediately invalidating the old one."""
    async with database_service.async_session_maker() as session:
        await verify_workspace_access(workspace_id, user, session)

        stmt = select(WidgetConfig).where(WidgetConfig.workspace_id == workspace_id)
        result = await session.execute(stmt)
        config = result.scalar_one_or_none()

        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Widget config not found",
            )

        old_key = config.widget_key
        config.widget_key = generate_widget_key()
        config.updated_at = datetime.now(UTC)

        session.add(config)
        await session.commit()
        await session.refresh(config)

        # Invalidate old key cache
        await cache_service.delete(f"widget_config:{old_key}")

        logger.info("widget_key_rotated", workspace_id=workspace_id)
        return _to_admin_response(config)


@router.post("/{workspace_id}/toggle", response_model=WidgetConfigAdminResponse)
async def toggle_widget(
    workspace_id: int,
    user: User = Depends(get_current_user),
):
    """Enable or disable the widget (toggles is_active)."""
    async with database_service.async_session_maker() as session:
        await verify_workspace_access(workspace_id, user, session)

        stmt = select(WidgetConfig).where(WidgetConfig.workspace_id == workspace_id)
        result = await session.execute(stmt)
        config = result.scalar_one_or_none()

        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Widget config not found",
            )

        config.is_active = not config.is_active
        config.updated_at = datetime.now(UTC)

        session.add(config)
        await session.commit()
        await session.refresh(config)

        # Invalidate cache
        await cache_service.delete(f"widget_config:{config.widget_key}")

        logger.info("widget_toggled", workspace_id=workspace_id, is_active=config.is_active)
        return _to_admin_response(config)


@router.get("/{workspace_id}/leads", response_model=list[LeadResponse])
async def list_leads(
    workspace_id: int,
    user: User = Depends(get_current_user),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """List leads captured by the widget for a workspace (paginated)."""
    async with database_service.async_session_maker() as session:
        await verify_workspace_access(workspace_id, user, session)

        stmt = (
            select(Lead)
            .where(Lead.workspace_id == workspace_id)
            .order_by(Lead.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        leads = result.scalars().all()

        return [
            LeadResponse(
                id=lead.id,
                workspace_id=lead.workspace_id,
                session_id=lead.session_id,
                email=lead.email,
                name=lead.name,
                metadata=lead.metadata_,
                created_at=lead.created_at,
            )
            for lead in leads
        ]
