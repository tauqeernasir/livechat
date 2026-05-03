# Project Progress: Lagent

## Module 1: Authentication & Onboarding
- [x] Backend Schema Update (Organization, Workspace, User)
- [x] Database Migrations (Alembic)
- [x] Onboarding Service Implementation
- [x] Onboarding API Endpoints (`/status`, `/profile`, `/workspace`)
- [x] Enhanced `/me` endpoint with onboarding status
- [x] S3/MinIO Storage Utility
- [x] Phase 2: Frontend Auth UI (Login, Register, AuthContext)
- [x] Phase 3: Onboarding Flow (Multi-step Wizard)

## Module 2: Knowledge Base & Training
- [x] Foundation & Models (Backend dependencies, SQLModels, pgvector migrations)
- [x] Data Ingestion (File Upload, TipTap Manual Entry)
- [x] Background Processing Pipeline (arq, Extraction Registry, Recursive Chunking)
- [x] Vector Storage (Embeddings with sentence-transformers, pgvector)
- [x] Guardrails & Persona Editor (AgentConfig API & UI)

## Module 3: Internal Testing Interface
- [ ] Playground UI
- [ ] Source Citations
- [ ] Knowledge Selection Toggle

## Module 4: The Chat Widget
- [ ] Widget Customization API
- [ ] Script Tag Delivery
- [ ] Lead Generation Form

## Module 5: Business Dashboard & Analytics
- [ ] Chat Logs
- [ ] Performance Metrics
- [ ] Subscription Management (Stripe)

---
### Notes
- Fixed Alembic `script.py.mako` template syntax error.
- Added `boto3` and `aiobotocore` for storage support.
- Implemented `/me` endpoint in `auth.py`.
- Added server default to `onboarding_completed` column in migration to handle existing data.
- Refactored `DatabaseService` to support `AsyncSession` using `postgresql+psycopg`.
- Refactored `OnboardingService` to use Dependency Injection and robust transaction handling.
- Installed `arq`, `pypdf`, `python-docx`, `langchain-text-splitters`, `sentence-transformers`, and `pgvector`.
- Configured Alembic with `pgvector` and `uv run ruff` post-write hooks.
- Successfully migrated `KnowledgeSource`, `DocumentChunk` (with vector support), and `AgentConfiguration` models.
- Implemented `KnowledgeService` with strategy-based extraction and chunking.
- Set up background worker with `arq` and corrected `RedisSettings` connectivity.
- Created reusable premium `Layout` and `Editor` (TipTap) components in React.
- Added Knowledge Base and Agent Training dashboards with real-time status polling.
