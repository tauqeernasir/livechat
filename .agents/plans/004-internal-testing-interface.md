# Plan: Internal Testing Interface (Module 3)

This plan outlines the steps to build the **Internal Testing Interface (Playground)**, allowing business owners to verify their AI agent's behavior, knowledge retrieval, and multi-session capabilities before deployment.

## Assessment
- **Complexity**: Medium
- **Execution mode**: Multiple phases (Backend API -> Frontend Base -> Streaming & Citations)
- **Sub-agent feasibility**: Yes
    - **Stream 1**: Backend API & Session Management.
    - **Stream 2**: Frontend UI Layout & Session History.
    - **Stream 3**: Streaming Logic & Citation Rendering.

## Clarifications & Assumptions
1.  **Agent Selection**: Since `AgentConfiguration` is currently 1:1 with `Workspace`, "Agent Selection" will involve switching between the user's available workspaces in the Playground.
2.  **Multiple Sessions**: We will support multiple chat sessions per workspace, displayed in a sidebar for easy switching.
3.  **Citations**: Sources will be displayed as a dedicated section immediately below each assistant response.
4.  **No Markdown**: For this phase, we will focus on plain text/pre-formatted output for speed and simplicity.

## Edge Cases & Risks
*   **Large Citation Lists**: If an answer uses many chunks, the citation list might grow long. We will implement a clean, scrollable or compact view.
*   **Stale Sessions**: Resetting a session must ensure all LangGraph checkpoints and local message states are cleared.
*   **Workspace Permissions**: Ensure users can only access sessions and knowledge for workspaces they belong to.

## Step-by-Step Plan

### Phase 1: Backend API Enhancements
1.  **Update Session Listing**:
    - [ ] Modify `GET /auth/sessions` (if needed) or create `GET /chatbot/sessions/{workspace_id}` to return all sessions for a specific agent/workspace.
2.  **Reset/Delete Session API**:
    - [ ] Create `DELETE /chatbot/session/{session_id}` in `backend/app/api/v1/chatbot.py`.
    - [ ] Ensure it calls `LangGraphAgent.clear_chat_history` and deletes the session record from the DB.
3.  **Source Metadata Cleanup**:
    - [ ] Update `search_knowledge_base` tool to return only the file basename for display, rather than internal S3 keys.

### Phase 2: Frontend Playground Foundation
1.  **Playground Page Structure**:
    - [ ] Create `frontend/src/pages/Playground.tsx`.
    - [ ] Implement a **Sidebar** for chat history/multiple sessions.
    - [ ] Implement a **Top Bar** with Agent (Workspace) selector.
2.  **Session Management Hook**:
    - [ ] Create `useChatSession` hook to handle switching between sessions and agents.

### Phase 3: Chat Interaction & Streaming
1.  **Streaming Consumer**:
    - [ ] Implement a streaming-capable chat client in the frontend to handle partial tokens from `/chatbot/chat/stream`.
2.  **Message Component**:
    - [ ] Build a `ChatMessage` component that renders:
        - The message text.
        - A **"Sources"** list below the text (only for assistant messages).
3.  **"New Chat" Logic**:
    - [ ] Add a button to the sidebar that creates a fresh session ID and clears the active chat window.

### Phase 4: UI/UX & Polish
1.  **Premium Styling**:
    - [ ] Apply "Premium Design" guidelines (gradients, subtle borders, Lucide icons).
    - [ ] Add smooth transitions for message entry.
2.  **Empty States**:
    - [ ] Add a "Welcome" screen when no session is selected, explaining how to start testing.

## Verification Strategy
- **Manual Test**: Switch between two different agents (workspaces) and verify that the session list updates correctly.
- **Manual Test**: Start a chat, verify tokens stream in, and citations appear at the end (or during) the response.
- **Database Audit**: Verify that "Reset Chat" correctly deletes checkpoints in the `checkpoints` table.

## Definition of Done
- [ ] Users can select which Agent (Workspace) to test via a dropdown.
- [ ] Users can maintain multiple distinct test sessions in a history sidebar.
- [ ] Assistant responses include a separate section for source citations.
- [ ] Real-time streaming is functional and visually polished.
- [ ] Session reset/deletion works end-to-end.
