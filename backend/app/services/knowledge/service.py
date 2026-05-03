"""Knowledge service for coordinating the processing pipeline."""

import os
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.models.knowledge import KnowledgeSource, DocumentChunk, SourceStatus, SourceType
from app.services.knowledge.strategies.extraction import ExtractionRegistry
from app.services.knowledge.strategies.chunking import RecursiveChunker
from app.services.knowledge.embeddings import EmbeddingServiceFactory
from app.utils.storage import storage_utils
from app.core.logging import logger


class KnowledgeService:
    """Service for managing knowledge source processing."""

    def __init__(
        self, 
        chunker=None, 
        embedding_service=None
    ):
        """Initialize with optional strategies."""
        self.chunker = chunker or RecursiveChunker()
        self.embedding_service = embedding_service or EmbeddingServiceFactory.get_service()

    async def process_source(self, session: AsyncSession, source_id: int):
        """Execute the full processing pipeline for a knowledge source.
        
        Pipeline: Download -> Extract -> Chunk -> Embed -> Store.
        """
        source = await session.get(KnowledgeSource, source_id)
        if not source:
            logger.error("source_not_found", source_id=source_id)
            return

        try:
            source.status = SourceStatus.PROCESSING
            session.add(source)
            await session.commit()

            # 1. Extraction
            text = ""
            if source.source_type == SourceType.FILE and source.file_key:
                # Download and extract from file
                content = await storage_utils.get_file(source.file_key)
                extension = os.path.splitext(source.name)[1]
                extractor = ExtractionRegistry.get_extractor(extension)
                text = extractor.extract(content)
            else:
                # Manual entry or already extracted text
                text = source.content or ""

            if not text:
                raise ValueError("No text extracted from source")

            source.content = text  # Cache extracted text
            
            # 2. Chunking
            chunks_text = self.chunker.chunk(text)
            
            # 3. Embedding (Batch)
            embeddings = await self.embedding_service.embed_batch(chunks_text)
            
            # 4. Storage
            # Clear existing chunks if any (re-processing)
            # Cascade delete should handle this if configured, but let's be explicit
            # Note: For simplicity in this MVP, we assume fresh processing
            
            db_chunks = [
                DocumentChunk(
                    source_id=source.id,
                    text=chunk_text,
                    vector=vector,
                    chunk_metadata={"index": i}
                )
                for i, (chunk_text, vector) in enumerate(zip(chunks_text, embeddings))
            ]
            
            session.add_all(db_chunks)
            
            source.status = SourceStatus.COMPLETED
            session.add(source)
            await session.commit()
            
            logger.info("source_processing_completed", source_id=source_id, chunks=len(db_chunks))

        except Exception as e:
            await session.rollback()
            logger.exception("source_processing_failed", source_id=source_id, error=str(e))
            source.status = SourceStatus.FAILED
            source.error_message = str(e)
            session.add(source)
            await session.commit()

    async def retrieve_relevant_chunks(
        self, session: AsyncSession, workspace_id: int, query: str, k: int = 4
    ) -> List[dict]:
        """Search for relevant chunks using vector similarity.
        
        Args:
            session: Async database session
            workspace_id: The ID of the workspace to search in
            query: User's natural language question
            k: Number of chunks to retrieve
            
        Returns:
            List[dict]: List of chunks with text and source metadata
        """
        try:
            # 1. Embed the query
            query_vectors = await self.embedding_service.embed_batch([query])
            query_vector = query_vectors[0]

            # 2. Similarity search with workspace scoping
            # We join with KnowledgeSource to ensure we only get chunks from the right workspace
            statement = (
                select(DocumentChunk, KnowledgeSource.name)
                .join(KnowledgeSource)
                .where(KnowledgeSource.workspace_id == workspace_id)
                .order_by(DocumentChunk.vector.cosine_distance(query_vector))
                .limit(k)
            )
            
            result = await session.execute(statement)
            rows = result.all()
            
            logger.info(
                "knowledge_retrieval_success", 
                workspace_id=workspace_id, 
                query=query, 
                chunks_found=len(rows)
            )
            
            return [
                {
                    "text": chunk.text,
                    "source": source_name,
                    "metadata": chunk.chunk_metadata
                }
                for chunk, source_name in rows
            ]
        except Exception as e:
            logger.exception("knowledge_retrieval_failed", workspace_id=workspace_id, error=str(e))
            return []


knowledge_service = KnowledgeService()
