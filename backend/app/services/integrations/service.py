"""Integration service — CRUD, spec sync, and workspace-scoped queries."""

from typing import List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.core.logging import logger
from app.models.integration import (
    Integration,
    IntegrationOperation,
    IntegrationStatus,
    IntegrationType,
)
from app.services.integrations.credentials import decrypt_credential, encrypt_credential
from app.services.integrations.openapi_parser import (
    extract_base_url,
    extract_operations,
    validate_openapi_spec,
)


# Maximum spec size when fetching from URL (2 MB)
MAX_SPEC_SIZE_BYTES = 2 * 1024 * 1024

# Timeout for fetching remote specs
SPEC_FETCH_TIMEOUT = 15


class IntegrationService:
    """Service for managing workspace integrations."""

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_integration(
        self,
        session: AsyncSession,
        workspace_id: int,
        *,
        name: str,
        spec_url: Optional[str] = None,
        spec_content: Optional[dict] = None,
        auth_type: str = "none",
        auth_header_name: str = "Authorization",
        credentials: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> Integration:
        """Create an integration and persist spec content.

        Either ``spec_url`` or ``spec_content`` must be provided.
        """
        if not spec_url and not spec_content:
            raise ValueError("Either spec_url or spec_content must be provided")

        # Fetch spec from URL if needed
        if spec_url and not spec_content:
            spec_content = await self._fetch_spec(spec_url)

        # Validate
        is_valid, error = validate_openapi_spec(spec_content)
        if not is_valid:
            raise ValueError(f"Invalid OpenAPI spec: {error}")

        encrypted_creds = encrypt_credential(credentials) if credentials else None

        # Derive base_url from spec if not explicitly provided
        if not base_url:
            base_url = extract_base_url(spec_content)

        integration = Integration(
            workspace_id=workspace_id,
            name=name,
            integration_type=IntegrationType.OPENAPI,
            spec_url=spec_url,
            spec_content=spec_content,
            auth_type=auth_type,
            auth_header_name=auth_header_name,
            encrypted_credentials=encrypted_creds,
            base_url=base_url,
            status=IntegrationStatus.PENDING,
            enabled=True,
        )
        session.add(integration)
        await session.flush()

        # Extract and persist operations
        operations = extract_operations(spec_content)
        for op in operations:
            session.add(
                IntegrationOperation(
                    integration_id=integration.id,
                    **op,
                    enabled=False,  # require explicit enablement
                )
            )

        await session.commit()
        await session.refresh(integration)

        logger.info(
            "integration_created",
            integration_id=integration.id,
            workspace_id=workspace_id,
            operations_count=len(operations),
        )

        integration.status = IntegrationStatus.ACTIVE
        session.add(integration)
        await session.commit()

        # Re-fetch with operations eagerly loaded for the response
        result = await session.execute(
            select(Integration)
            .options(selectinload(Integration.operations))
            .where(Integration.id == integration.id)
        )
        return result.scalar_one()

    async def get_integration(
        self, session: AsyncSession, integration_id: int, workspace_id: int
    ) -> Optional[Integration]:
        """Get a single integration scoped to a workspace."""
        result = await session.execute(
            select(Integration)
            .options(selectinload(Integration.operations))
            .where(
                Integration.id == integration_id,
                Integration.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_integrations(
        self, session: AsyncSession, workspace_id: int
    ) -> List[Integration]:
        """List all integrations for a workspace."""
        result = await session.execute(
            select(Integration)
            .options(selectinload(Integration.operations))
            .where(Integration.workspace_id == workspace_id)
        )
        return list(result.scalars().all())

    async def update_integration(
        self,
        session: AsyncSession,
        integration: Integration,
        *,
        name: Optional[str] = None,
        auth_type: Optional[str] = None,
        auth_header_name: Optional[str] = None,
        credentials: Optional[str] = None,
        base_url: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> Integration:
        """Partial update of an integration."""
        if name is not None:
            integration.name = name
        if auth_type is not None:
            integration.auth_type = auth_type
        if auth_header_name is not None:
            integration.auth_header_name = auth_header_name
        if credentials is not None:
            integration.encrypted_credentials = encrypt_credential(credentials)
        if base_url is not None:
            integration.base_url = base_url
        if enabled is not None:
            integration.enabled = enabled

        session.add(integration)
        await session.commit()

        # Re-fetch with operations eagerly loaded
        result = await session.execute(
            select(Integration)
            .options(selectinload(Integration.operations))
            .where(Integration.id == integration.id)
        )
        return result.scalar_one()

    async def delete_integration(
        self, session: AsyncSession, integration: Integration
    ) -> None:
        """Delete an integration and its operations (cascade)."""
        await session.delete(integration)
        await session.commit()
        logger.info("integration_deleted", integration_id=integration.id)

    async def toggle_operations(
        self,
        session: AsyncSession,
        integration_id: int,
        operation_ids: List[int],
        enabled: bool,
    ) -> int:
        """Enable or disable a set of operations. Returns count updated."""
        result = await session.execute(
            select(IntegrationOperation).where(
                IntegrationOperation.integration_id == integration_id,
                IntegrationOperation.id.in_(operation_ids),
            )
        )
        ops = list(result.scalars().all())
        for op in ops:
            op.enabled = enabled
            session.add(op)
        await session.commit()
        return len(ops)

    async def resync_spec(
        self, session: AsyncSession, integration: Integration
    ) -> Integration:
        """Re-fetch and re-parse the spec, updating operations."""
        if not integration.spec_url:
            raise ValueError("Integration has no spec_url to sync from")

        integration.status = IntegrationStatus.SYNCING
        session.add(integration)
        await session.commit()

        try:
            spec_content = await self._fetch_spec(integration.spec_url)
            is_valid, error = validate_openapi_spec(spec_content)
            if not is_valid:
                raise ValueError(f"Invalid OpenAPI spec: {error}")

            integration.spec_content = spec_content
            if not integration.base_url:
                integration.base_url = extract_base_url(spec_content)

            # Replace operations: delete old, insert new
            old_ops = await session.execute(
                select(IntegrationOperation).where(
                    IntegrationOperation.integration_id == integration.id
                )
            )
            for op in old_ops.scalars().all():
                await session.delete(op)

            new_ops = extract_operations(spec_content)
            for op in new_ops:
                session.add(
                    IntegrationOperation(
                        integration_id=integration.id, **op, enabled=False
                    )
                )

            integration.status = IntegrationStatus.ACTIVE
            integration.error_message = None
            session.add(integration)
            await session.commit()
            await session.refresh(integration)

            logger.info(
                "integration_resynced",
                integration_id=integration.id,
                operations_count=len(new_ops),
            )
            return integration

        except Exception as e:
            integration.status = IntegrationStatus.ERROR
            integration.error_message = str(e)[:500]
            session.add(integration)
            await session.commit()
            await session.refresh(integration)
            logger.error(
                "integration_resync_failed",
                integration_id=integration.id,
                error=str(e),
            )
            raise

    # ------------------------------------------------------------------
    # Workspace-scoped queries for runtime
    # ------------------------------------------------------------------

    async def get_enabled_operations(
        self, session: AsyncSession, workspace_id: int
    ) -> List[dict]:
        """Return all enabled operations for active integrations in a workspace.

        Returns list of dicts with integration metadata + operation details.
        """
        result = await session.execute(
            select(Integration, IntegrationOperation)
            .join(IntegrationOperation)
            .where(
                Integration.workspace_id == workspace_id,
                Integration.enabled.is_(True),
                Integration.status == IntegrationStatus.ACTIVE,
                IntegrationOperation.enabled.is_(True),
            )
        )
        rows = result.all()
        ops = []
        for integration, operation in rows:
            ops.append(
                {
                    "integration_id": integration.id,
                    "integration_name": integration.name,
                    "base_url": integration.base_url,
                    "auth_type": integration.auth_type,
                    "auth_header_name": integration.auth_header_name,
                    "encrypted_credentials": integration.encrypted_credentials,
                    "operation_id": operation.operation_id,
                    "method": operation.method,
                    "path": operation.path,
                    "summary": operation.summary,
                    "description": operation.description,
                    "parameters_schema": operation.parameters_schema,
                    "response_schema": operation.response_schema,
                }
            )
        return ops

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_spec(self, url: str) -> dict:
        """Fetch an OpenAPI spec from a URL with size and timeout limits."""
        async with httpx.AsyncClient(timeout=SPEC_FETCH_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            if len(response.content) > MAX_SPEC_SIZE_BYTES:
                raise ValueError(
                    f"Spec exceeds maximum size of {MAX_SPEC_SIZE_BYTES // 1024}KB"
                )

            return response.json()


integration_service = IntegrationService()
