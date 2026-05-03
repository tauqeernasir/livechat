"""Onboarding schemas."""

from typing import Optional
from pydantic import BaseModel
from app.schemas.base import BaseResponse


class OrganizationCreate(BaseModel):
    """Schema for creating an organization during onboarding."""
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None


class BrandIdentityUpdate(BaseModel):
    """Schema for updating brand identity during onboarding."""
    primary_color: str = "#4f46e5"


class WorkspaceCreate(BaseModel):
    """Schema for creating a workspace during onboarding."""
    name: str
    timezone: Optional[str] = "UTC"


class OnboardingStatusResponse(BaseResponse):
    """Response schema for onboarding status."""
    onboarding_completed: bool
    has_organization: bool
    has_workspace: bool
