# Plan: RAG and Agent Configuration Integration

This plan outlines the steps to bridge the Knowledge Base (Module 2) with the LangGraph Agent, enabling RAG (Retrieval-Augmented Generation) and dynamic persona management.

## Assessment
- **Complexity**: Medium
- **Execution mode**: Multiple phases (Schema -> Logic -> Integration)
- **Sub-agent feasibility**: Yes
    - **Stream 1**: Database & Schema updates (Session model).
    - **Stream 2**: RAG Logic (Retrieval method in `KnowledgeService`).
    - **Stream 3**: Agent Integration (LangGraph tool and dynamic prompts).

## Clarifications & Assumptions
1.  **Workspace Discovery**: Currently, the `Session` model does not store which `Workspace` it belongs to. Since RAG must be scoped to a workspace, we will add `workspace_id` to the `Session` table.
2.  **Embedding Model**: We will use the same `all-MiniLM-L6-v2` (384 dimensions) model for generating query embeddings as used for chunking.
3.  **Search Parameters**: Default to Top-4 (`k=4`) most relevant chunks.
4.  **Prompt Injection**: Persona and fallback rules will be injected into the system prompt with clear Markdown headers.

## Edge Cases & Risks
*   **Empty Knowledge Base**: RAG tool must return a "No information found" message gracefully.
*   **Context Window**: Large chunks might overflow the LLM context. We will implement a character limit on retrieved context.
*   **Missing Agent Config**: Fall back to project defaults if no config is found for a workspace.

## Step-by-Step Plan

### Phase 1: Database & Schema (The Foundation)
1.  **Modify `Session` Model**:
    - [ ] Update `backend/app/models/session.py` to add `workspace_id: int = Field(foreign_key="workspace.id", index=True)`.
2.  **Update `DatabaseService`**:
    - [ ] Update `create_session` in `backend/app/services/database.py` to accept and store `workspace_id`.
3.  **Database Migration**:
    - [ ] Generate and apply Alembic migration for the `Session.workspace_id` column.
4.  **Update Auth API**:
    - [ ] Update the `create_session` endpoint in `backend/app/api/v1/auth.py` to resolve the user's default `workspace_id` (or one passed in the request) and store it in the session.

### Phase 2: RAG Retrieval Logic
1.  **Update `KnowledgeService`**:
    - [ ] Add `retrieve_relevant_chunks(workspace_id, query, k=4)` in `backend/app/services/knowledge/service.py`.
    - [ ] Implement embedding of the query and similarity search using `pgvector`.
2.  **Create LangGraph Tool**:
    - [ ] Create `backend/app/core/langgraph/tools/knowledge_base.py` with a `search_knowledge_base` tool.
    - [ ] Ensure the tool returns a formatted string containing both text and source citations.
3.  **Register Tool**:
    - [ ] Export the new tool in `backend/app/core/langgraph/tools/__init__.py`.

### Phase 3: Agent Integration
1.  **Update Prompt Loading**:
    - [ ] Modify `load_system_prompt` in `backend/app/core/prompts/__init__.py` to accept `persona` and `fallback_rule`.
2.  **Update `LangGraphAgent`**:
    - [ ] In `_chat` node, fetch the `AgentConfiguration` for the session's `workspace_id`.
    - [ ] Inject configuration into the system prompt.
    - [ ] Bind the `search_knowledge_base` tool to the LLM.
3.  **Validation**:
    - [ ] Ensure the agent prioritizes knowledge base info but adheres to the "persona" and "fallback rules" (e.g., if no info found, follow fallback instructions).

## Verification Strategy
- **Unit Test**: Test retrieval logic independently with a script in `scratch/`.
- **Integration Test**: Manual end-to-end test via `/chat` endpoint asking about a specific uploaded document.
- **Log Audit**: Verify that the correct `workspace_id` and `AgentConfig` are loaded per request in the logs.

## Definition of Done
- [ ] Agent successfully calls `search_knowledge_base` for relevant queries.
- [ ] Responses include source citations (e.g., `[Source: company_policy.pdf]`).
- [ ] Agent's tone and fallback behavior matches the settings in the dashboard.
- [ ] All sessions are correctly linked to a workspace.
