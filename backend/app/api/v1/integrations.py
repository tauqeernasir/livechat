"""Integration management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.logging import logger
from app.models.user import User
from app.schemas.integration import (
    IntegrationCreate,
    IntegrationListResponse,
    IntegrationResponse,
    IntegrationSyncResponse,
    IntegrationUpdate,
    OperationToggle,
)
from app.services.database import database_service
from app.services.integrations.service import integration_service
from app.utils.workspace import verify_workspace_access

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=IntegrationResponse)
async def create_integration(
    workspace_id: int,
    data: IntegrationCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Create a new OpenAPI integration for a workspace."""
    await verify_workspace_access(workspace_id, current_user, session)

    try:
        integration = await integration_service.create_integration(
            session,
            workspace_id,
            name=data.name,
            spec_url=data.spec_url,
            spec_content=data.spec_content,
            auth_type=data.auth_type,
            auth_header_name=data.auth_header_name,
            credentials=data.credentials,
            base_url=data.base_url,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return integration


@router.get("", response_model=IntegrationListResponse)
async def list_integrations(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """List all integrations for a workspace."""
    await verify_workspace_access(workspace_id, current_user, session)
    integrations = await integration_service.list_integrations(session, workspace_id)
    return IntegrationListResponse(integrations=integrations)


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    workspace_id: int,
    integration_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Get a single integration by ID."""
    await verify_workspace_access(workspace_id, current_user, session)
    integration = await integration_service.get_integration(
        session, integration_id, workspace_id
    )
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
        )
    return integration


@router.patch("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    workspace_id: int,
    integration_id: int,
    data: IntegrationUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Update an integration's config (name, auth, enabled)."""
    await verify_workspace_access(workspace_id, current_user, session)
    integration = await integration_service.get_integration(
        session, integration_id, workspace_id
    )
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
        )

    integration = await integration_service.update_integration(
        session,
        integration,
        name=data.name,
        auth_type=data.auth_type,
        auth_header_name=data.auth_header_name,
        credentials=data.credentials,
        base_url=data.base_url,
        enabled=data.enabled,
    )
    return integration


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    workspace_id: int,
    integration_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Delete an integration and all its operations."""
    await verify_workspace_access(workspace_id, current_user, session)
    integration = await integration_service.get_integration(
        session, integration_id, workspace_id
    )
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
        )
    await integration_service.delete_integration(session, integration)


@router.post("/{integration_id}/sync", response_model=IntegrationSyncResponse)
async def sync_integration(
    workspace_id: int,
    integration_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Re-fetch and re-parse the OpenAPI spec."""
    await verify_workspace_access(workspace_id, current_user, session)
    integration = await integration_service.get_integration(
        session, integration_id, workspace_id
    )
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
        )

    try:
        await integration_service.resync_spec(session, integration)
        return IntegrationSyncResponse(
            integration_id=integration.id,
            status="active",
            message="Spec synced successfully",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.post("/{integration_id}/operations/toggle")
async def toggle_operations(
    workspace_id: int,
    integration_id: int,
    data: OperationToggle,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Enable or disable specific operations."""
    await verify_workspace_access(workspace_id, current_user, session)
    integration = await integration_service.get_integration(
        session, integration_id, workspace_id
    )
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
        )

    count = await integration_service.toggle_operations(
        session, integration_id, data.operation_ids, data.enabled
    )
    return {"updated": count}
