"""Onboarding API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.schemas.onboarding import (
    OrganizationCreate,
    WorkspaceCreate,
    OnboardingStatusResponse,
)
from app.services.onboarding import onboarding_service
from app.services.database import database_service
from app.core.logging import logger

router = APIRouter()


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session)
):
    """Get the current onboarding status for the authenticated user.

    Returns:
        OnboardingStatusResponse: Status flags for onboarding.
    """
    logger.info("get_onboarding_status_called", user_id=user.id)
    status_data = await onboarding_service.get_onboarding_status(session, user.id)
    return OnboardingStatusResponse(**status_data)


@router.post("/profile", status_code=status.HTTP_201_CREATED)
async def create_business_profile(
    org_data: OrganizationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session)
):
    """Create a business profile (Organization) for the user.

    Args:
        org_data: Organization details.
        user: The authenticated user.
        session: Async database session.

    Returns:
        dict: The created organization details.
    """
    logger.info("create_business_profile_called", user_id=user.id, org_name=org_data.name)
    org = await onboarding_service.create_organization(session, user.id, org_data)
    return org


@router.post("/workspace", status_code=status.HTTP_201_CREATED)
async def create_default_workspace(
    ws_data: WorkspaceCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session)
):
    """Create the initial default workspace for the user's organization.

    Args:
        ws_data: Workspace details.
        user: The authenticated user.
        session: Async database session.

    Returns:
        dict: The created workspace details.

    Raises:
        HTTPException: If the user doesn't have an organization yet.
    """
    logger.info("create_default_workspace_called", user_id=user.id, ws_name=ws_data.name)
    
    if not user.organization_id:
        logger.error("workspace_creation_failed_no_org", user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business profile must be created before a workspace."
        )
    
    workspace = await onboarding_service.create_workspace(
        session, user.organization_id, ws_data, is_default=True
    )
    
    # Mark onboarding as complete
    await onboarding_service.complete_onboarding(session, user.id)
    
    return workspace
