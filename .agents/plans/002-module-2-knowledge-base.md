# Implementation Plan: Module 2 - Knowledge Base & Training

## 1. Assessment
- **Complexity**: High
- **Execution mode**: Multiple phases
- **Sub-agent feasibility**: Yes
    - **Stream A**: Backend Models, Migrations, and Basic APIs.
    - **Stream B**: Background Processing Pipeline (S3, Extraction, Chunking, Embedding).
    - **Stream C**: Frontend UI (Uploads, Tracking, TipTap Editor, Configuration).

## 2. Assumptions
- **Storage**: We will use the existing S3/MinIO infrastructure for raw file storage.
- **Worker**: We will use `arq` (Redis-based) for background tasks, leveraging the existing Valkey service.
- **Embeddings**: `sentence-transformers` (e.g., `all-MiniLM-L6-v2`) will be the default local open-source model.
- **Database**: `pgvector` is enabled on the `db` service.

## 3. Edge Cases and Risks
- **Large File Processing**: Timeouts or memory issues during extraction of 10MB PDFs. *Mitigation: Background workers with resource limits.*
- **Malformed Documents**: Unsupported PDF versions or corrupted Docx files. *Mitigation: Robust error handling and status tracking.*
- **Embedding Dimensions**: Swapping models might change vector dimensions. *Mitigation: Ensure vector columns are updated or dimension-agnostic where possible.*
- **Concurrency**: Multiple uploads for the same workspace. *Mitigation: Atomic status updates and job locking.*

## 4. Step-by-Step Plan

### Phase 1: Foundation & Models
1.  **Install Dependencies**:
    *   Backend: `arq`, `pypdf`, `python-docx`, `langchain-text-splitters`, `sentence-transformers`.
    *   Frontend: `@tiptap/react`, `@tiptap/starter-kit`.
2.  **Define Models**:
    *   `KnowledgeSource`: Tracks files/manual entries (Status: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`).
    *   `DocumentChunk`: Stores text and `Vector` (pgvector).
    *   `AgentConfiguration`: Persona, Fallback rules, linked to Workspace.
3.  **Migrations**: Generate and apply Alembic migrations for new tables and relationships.

### Phase 2: Background Processing Pipeline
1.  **Task Queue Setup**: Configure `arq` worker to connect to Valkey.
2.  **Extraction Strategies**: Implement generic interfaces for `TextExtractor` (PDF, Docx, TXT).
3.  **Chunking Strategies**: Implement `RecursiveCharacterTextSplitter` strategy via a strategy pattern.
4.  **Embedding Interface**: Create a `BaseEmbeddingService` and a local implementation using `sentence-transformers`.
5.  **Processing Logic**: Implement the pipeline: `Download from S3` -> `Extract` -> `Chunk` -> `Embed` -> `Store in Vector DB`.

### Phase 3: Backend API Development
1.  **Knowledge Base Endpoints**:
    *   `POST /knowledge/upload`: Receive file, save to S3, trigger background job.
    *   `POST /knowledge/manual`: Save TipTap content directly to processing.
    *   `GET /knowledge/status/{id}`: Poll for processing status.
2.  **Agent Config Endpoints**:
    *   `GET/PATCH /workspaces/{id}/config`: Manage Persona and Fallback rules.

### Phase 4: Frontend Implementation
1.  **Knowledge Base Dashboard**: Page to list and manage sources.
2.  **Upload Component**: Drag-and-drop with progress bars and status indicators.
3.  **TipTap Integration**: Custom editor component for manual policy entry.
4.  **Configuration Wizard**: UI to edit AI Persona and system rules.

## 5. Verification Strategy
- **Unit Tests**: Test extraction and chunking strategies in isolation.
- **Integration Tests**: Mock S3 and verify the full worker pipeline from upload to vector storage.
- **UI Verification**: Manual verification of upload progress and TipTap content persistence.

## 6. Definition of Done
- [ ] Files can be uploaded and stored in S3.
- [ ] Text is extracted, chunked, and embedded via background workers.
- [ ] Embeddings are stored in Postgres using pgvector.
- [ ] Agent configurations (Persona/Fallback) are persisted and editable.
- [ ] Frontend displays processing status and provides a rich-text editing experience.
