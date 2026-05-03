"""Knowledge base API endpoints."""

import os
from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.models.knowledge import KnowledgeSource, SourceType, SourceStatus
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.services.database import database_service
from app.services.tasks import task_queue_service
from app.utils.storage import storage_utils
from app.schemas.knowledge import ManualKnowledgeCreate
from app.core.logging import logger

router = APIRouter()


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_knowledge_file(
    workspace_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Upload a file to the knowledge base and trigger processing."""
    # 1. Validation
    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in [".pdf", ".docx", ".txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {extension}. Supported: .pdf, .docx, .txt"
        )

    # 2. Save to S3
    try:
        content = await file.read()
        file_key = f"workspaces/{workspace_id}/knowledge/{file.filename}"
        await storage_utils.upload_file(content, file_key)
        
        # 3. Create database entry
        source = KnowledgeSource(
            workspace_id=workspace_id,
            source_type=SourceType.FILE,
            name=file.filename,
            file_key=file_key,
            status=SourceStatus.PENDING
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)
        
        # 4. Trigger background task
        await task_queue_service.enqueue_knowledge_processing(source.id)
        
        logger.info("knowledge_upload_success", source_id=source.id, filename=file.filename)
        return {"source_id": source.id, "status": source.status}
        
    except Exception as e:
        logger.exception("knowledge_upload_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload and process file"
        )


@router.post("/manual", status_code=status.HTTP_201_CREATED)
async def add_manual_knowledge(
    workspace_id: int,
    data: ManualKnowledgeCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Add manual text knowledge (from TipTap) and trigger processing."""
    try:
        source = KnowledgeSource(
            workspace_id=workspace_id,
            source_type=SourceType.MANUAL,
            name=data.name,
            content=data.content,
            status=SourceStatus.PENDING
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)
        
        # Trigger background task
        await task_queue_service.enqueue_knowledge_processing(source.id)
        
        return {"source_id": source.id, "status": source.status}
    except Exception as e:
        logger.exception("manual_knowledge_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save manual knowledge"
        )


@router.get("/sources/{workspace_id}", response_model=List[dict])
async def list_knowledge_sources(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """List all knowledge sources for a workspace."""
    statement = select(KnowledgeSource).where(KnowledgeSource.workspace_id == workspace_id)
    result = await session.execute(statement)
    sources = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "name": s.name,
            "source_type": s.source_type,
            "status": s.status,
            "created_at": s.created_at,
            "error_message": s.error_message
        }
        for s in sources
    ]


@router.get("/status/{source_id}")
async def get_source_status(
    source_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Get the processing status of a specific source."""
    source = await session.get(KnowledgeSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
        
    return {
        "id": source.id,
        "status": source.status,
        "error_message": source.error_message
    }
