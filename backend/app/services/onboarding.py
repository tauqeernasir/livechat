"""Onboarding service for handling business profile and workspace setup."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from fastapi import HTTPException, status
from app.models import Organization, Workspace, User
from app.schemas.onboarding import OrganizationCreate, WorkspaceCreate
from app.core.logging import logger


class OnboardingService:
    """Service for managing the user onboarding flow."""

    async def create_organization(self, session: AsyncSession, user_id: int, org_data: OrganizationCreate) -> Organization:
        """Create a new organization and link it to the user.

        Args:
            session: Async database session
            user_id: ID of the user creating the organization
            org_data: Organization details

        Returns:
            Organization: The created organization
        """
        try:
            # Check if user already has an organization
            user = await session.get(User, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
                
            if user.organization_id:
                logger.warning("user_already_has_organization", user_id=user_id, org_id=user.organization_id)
                org = await session.get(Organization, user.organization_id)
                return org

            org = Organization(**org_data.model_dump())
            session.add(org)
            await session.flush()  # Get org.id

            user.organization_id = org.id
            session.add(user)
            
            await session.commit()
            await session.refresh(org)
            logger.info("organization_created", org_id=org.id, user_id=user_id)
            return org
        except IntegrityError:
            await session.rollback()
            logger.warning("organization_creation_race_condition", user_id=user_id)
            # Re-fetch user to get the organization_id that was likely set by another concurrent request
            await session.refresh(user)
            if user.organization_id:
                return await session.get(Organization, user.organization_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Organization creation failed due to a concurrency issue."
            )
        except Exception as e:
            await session.rollback()
            logger.error("organization_creation_failed", error=str(e), user_id=user_id)
            raise

    async def create_workspace(self, session: AsyncSession, org_id: int, ws_data: WorkspaceCreate, is_default: bool = False) -> Workspace:
        """Create a new workspace for an organization.

        Args:
            session: Async database session
            org_id: ID of the organization
            ws_data: Workspace details
            is_default: Whether this is the default workspace

        Returns:
            Workspace: The created workspace
        """
        try:
            # Validate organization exists
            org = await session.get(Organization, org_id)
            if not org:
                raise HTTPException(status_code=404, detail="Organization not found")

            workspace = Workspace(
                org_id=org_id, 
                name=ws_data.name, 
                timezone=ws_data.timezone,
                is_default=is_default
            )
            session.add(workspace)
            await session.commit()
            await session.refresh(workspace)
            logger.info("workspace_created", workspace_id=workspace.id, org_id=org_id)
            return workspace
        except Exception as e:
            await session.rollback()
            logger.error("workspace_creation_failed", error=str(e), org_id=org_id)
            raise

    async def complete_onboarding(self, session: AsyncSession, user_id: int) -> bool:
        """Mark onboarding as completed for a user.

        Args:
            session: Async database session
            user_id: ID of the user

        Returns:
            bool: True if successful
        """
        try:
            user = await session.get(User, user_id)
            if not user:
                return False
            
            user.onboarding_completed = True
            session.add(user)
            await session.commit()
            logger.info("onboarding_completed", user_id=user_id)
            return True
        except Exception as e:
            await session.rollback()
            logger.error("complete_onboarding_failed", error=str(e), user_id=user_id)
            return False

    async def get_onboarding_status(self, session: AsyncSession, user_id: int) -> dict:
        """Get the current onboarding status for a user.

        Args:
            session: Async database session
            user_id: ID of the user

        Returns:
            dict: Status flags
        """
        # Optimized: Fetch only needed columns
        result = await session.execute(
            select(User.onboarding_completed, User.organization_id).where(User.id == user_id)
        )
        user_data = result.first()
        
        if not user_data:
            return {
                "onboarding_completed": False,
                "has_organization": False,
                "has_workspace": False
            }
            
        has_org = user_data.organization_id is not None
        has_ws = False
        if has_org:
            ws_result = await session.execute(
                select(Workspace.id).where(Workspace.org_id == user_data.organization_id).limit(1)
            )
            has_ws = ws_result.first() is not None
        
        return {
            "onboarding_completed": user_data.onboarding_completed,
            "has_organization": has_org,
            "has_workspace": has_ws
        }


onboarding_service = OnboardingService()
