# Plan: The Chat Widget (Module 4)

An embeddable, lightweight chat widget that businesses copy-paste into their websites. End-users (visitors) interact with the AI agent without needing an account. The widget must be **fully tenant-isolated** — each widget instance is cryptographically bound to a single workspace, and no data can leak across organizations.

## Assessment
- **Complexity**: High
- **Execution mode**: Multiple phases (Security Model → Backend APIs → Widget Bundle → Lead Capture)
- **Sub-agent feasibility**: Yes
    - **Stream 1**: Backend — Widget auth, public API, tenant isolation
    - **Stream 2**: Widget — Shadow DOM bundle, streaming, customization
    - **Stream 3**: Lead capture — Optional gating form, lead storage

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  Business Owner's Website                       │
│                                                 │
│  <script src="https://api.lagent.ai/widget/     │
│    embed.js?key=wk_abc123"></script>             │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  Shadow DOM (CSS-isolated)                │  │
│  │  ┌─────────────────────────────────┐      │  │
│  │  │  Chat Widget (Preact)           │      │  │
│  │  │  - Bubble icon                  │      │  │
│  │  │  - Chat panel                   │      │  │
│  │  │  - Lead form (optional)         │      │  │
│  │  └─────────────────────────────────┘      │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
        │  HTTPS (SSE streaming)
        ▼
┌─────────────────────────────────────────────────┐
│  Backend — /api/v1/widget/*                     │
│                                                 │
│  1. Widget Key validation (wk_xxx → workspace)  │
│  2. Anonymous session creation (scoped)         │
│  3. Chat (reuses LangGraphAgent)                │
│  4. Tenant isolation at every layer             │
└─────────────────────────────────────────────────┘
```

## Security Model — Multi-Tenant Isolation

This is the most critical design decision. Every layer enforces isolation:

### 1. Widget Keys (Public API Keys)
- Each workspace gets a **publishable widget key** (`wk_` prefix) stored in a new `WidgetConfig` model.
- Widget keys are **not secrets** — they are embedded in `<script>` tags on public websites. They identify which workspace the widget belongs to, similar to Stripe's `pk_` keys.
- The key is validated on every request and resolved to a `workspace_id`. All downstream queries are scoped to that workspace.
- Widget keys can be **rotated** by the business owner without downtime (old key invalidated immediately).

### 2. Anonymous Sessions
- End-users don't authenticate. The widget creates an **anonymous session** via `POST /api/v1/widget/session`.
- Anonymous sessions have `user_id = NULL` and a special `source = "widget"` marker.
- Sessions receive a short-lived JWT (`type = "widget_session"`) that is **bound to the workspace_id** in its claims.
- The JWT is stored in the widget's runtime memory (not localStorage — avoids XSS persistence).

### 3. Request-Level Isolation
- A new `get_widget_session` dependency validates:
  1. The JWT is a `widget_session` type.
  2. The `workspace_id` in the JWT matches the `workspace_id` on the session record.
  3. The session's `workspace_id` is used for all downstream queries (RAG, agent config).
- **No cross-workspace access is possible** — the workspace_id is embedded in the JWT at session creation and re-verified on every request.

### 4. Rate Limiting & Abuse Prevention
- Widget endpoints have **aggressive rate limits** (separate from dashboard limits).
- Per-IP and per-session rate limiting to prevent abuse.
- Optional CORS restriction: widget key can be bound to specific `allowed_origins` so only the business's own domain can use it.

### 5. Data Isolation Summary
| Layer | Isolation Mechanism |
|-------|-------------------|
| Widget Key | Maps to exactly one workspace |
| JWT Claims | `workspace_id` + `type=widget_session` baked into token |
| Session Record | `workspace_id` FK, `source=widget` |
| RAG Retrieval | Already scoped by `workspace_id` (Module 3) |
| Agent Config | Already scoped by `workspace_id` (Module 3) |
| Chat History | Session-scoped, session is workspace-scoped |
| Leads | FK to workspace, not shared across orgs |

## Clarifications & Assumptions
1. **Widget Framework**: Use **Preact** (~3KB gzipped) instead of React to keep the bundle lightweight (<30KB total). The widget is a separate build artifact, not part of the dashboard React app.
2. **Shadow DOM**: All widget markup and styles are encapsulated in a Shadow DOM to prevent CSS conflicts with the host page.
3. **No localStorage**: Widget session tokens are held in JS closure memory only. Page refresh = new session. This is intentional for security (prevents XSS token theft) and simplicity.
4. **Streaming**: Widget uses the same SSE streaming pattern as the Playground (`text/event-stream`).
5. **Customization Storage**: Visual settings (color, position, welcome message) are stored in a new `WidgetConfig` model, not in `AgentConfiguration` (separation of concerns — agent behavior vs. widget appearance).
6. **Embed Script**: A tiny (~1KB) loader script that injects the full widget bundle. The loader is served from our backend as a static asset.

## Edge Cases & Risks
- **CORS**: Widget requests come from arbitrary third-party domains. The widget API endpoints must have permissive CORS (`*`) but validate the `widget_key` instead. Dashboard API endpoints keep restricted CORS.
- **Widget Key Leakage**: Keys are public by design (like Stripe publishable keys). Security comes from rate limiting + origin restrictions, not key secrecy.
- **Session Expiry**: Widget JWTs should be short-lived (e.g., 4 hours). If expired mid-conversation, the widget silently creates a new session and shows a "Session refreshed" notice.
- **Large Traffic Spikes**: A popular business site could generate many concurrent widget sessions. Rate limiting per-key prevents a single workspace from overwhelming the system.
- **XSS on Host Page**: Since we use Shadow DOM and don't persist tokens, XSS on the host page cannot steal session tokens or inject into the widget DOM.

## Pre-requisites (from existing modules)

These are already implemented and will be reused:
- [x] `LangGraphAgent` with `get_stream_response` (Module 3)
- [x] `workspace_id` on Session model (Module 3)
- [x] RAG scoped by `workspace_id` (Module 3)
- [x] `AgentConfiguration` per workspace (Module 2)
- [x] `Organization → Workspace` hierarchy (Module 1)
- [x] JWT creation utility (`create_access_token`) (Module 1)

## Step-by-Step Plan

### Phase 1: Data Model & Widget Key Infrastructure

1. **Create `WidgetConfig` model**:
    - [ ] Create `backend/app/models/widget_config.py` with fields:
        - `id: int` (PK)
        - `workspace_id: int` (FK, unique — one config per workspace)
        - `widget_key: str` (unique, indexed — the publishable key, e.g., `wk_a1b2c3d4e5`)
        - `is_active: bool` (default True — master toggle)
        - `allowed_origins: list[str]` (JSON column — optional CORS lock-down)
        - `position: str` (default `"bottom-right"`, enum: bottom-right | bottom-left)
        - `primary_color: str` (default from org's `primary_color`)
        - `welcome_message: str` (default "Hi! How can I help you today?")
        - `placeholder_text: str` (default "Type your message...")
        - `icon_url: Optional[str]` (custom launcher icon, nullable)
        - `lead_capture_enabled: bool` (default False)
        - `lead_capture_fields: list[str]` (JSON, default `["email"]`)
        - `updated_at: datetime`
    - [ ] Register in `backend/app/models/__init__.py`.

2. **Update `Session` model**:
    - [ ] Add `source: str = Field(default="dashboard")` — values: `"dashboard"` | `"widget"`.
    - [ ] Make `user_id` nullable (`Optional[int]`) to support anonymous widget sessions.

3. **Create Alembic migration**:
    - [ ] Generate migration for `WidgetConfig` table and `Session` column changes.

4. **Widget key generation utility**:
    - [ ] Create `backend/app/utils/widget_keys.py` with `generate_widget_key() -> str` that produces `wk_` + 24 char URL-safe random string using `secrets.token_urlsafe`.

### Phase 2: Widget Backend API

1. **Create widget API router**:
    - [ ] Create `backend/app/api/v1/widget.py` with a dedicated `APIRouter`.
    - [ ] Register in `backend/app/api/v1/api.py` at prefix `/widget`.

2. **Widget key validation dependency**:
    - [ ] Create `get_widget_config(x_widget_key: str = Header(...))` dependency that:
        - Looks up `WidgetConfig` by `widget_key`.
        - Validates `is_active = True`.
        - Optionally checks `Origin` header against `allowed_origins`.
        - Returns the `WidgetConfig` (which carries `workspace_id`).
    - [ ] Cache widget key lookups in Valkey/Redis (TTL ~60s) to avoid DB hits on every request.

3. **Anonymous session endpoint**:
    - [ ] `POST /api/v1/widget/session` — accepts widget key (header), creates an anonymous session:
        - `session_id = uuid4()`
        - `user_id = None`
        - `workspace_id` from widget config
        - `source = "widget"`
        - Returns a short-lived JWT (`type = "widget_session"`, `exp = 4h`) and session_id.

4. **Widget session auth dependency**:
    - [ ] Create `get_widget_session(credentials)` dependency that:
        - Decodes the JWT, verifies `type == "widget_session"`.
        - Loads the Session record.
        - Asserts `session.source == "widget"` and `session.workspace_id` matches JWT claim.
        - Returns the Session.

5. **Chat endpoints (widget-scoped)**:
    - [ ] `POST /api/v1/widget/chat/stream` — SSE streaming, uses `get_widget_session`, delegates to `LangGraphAgent.get_stream_response`.
    - [ ] `GET /api/v1/widget/messages` — returns chat history for the widget session.
    - [ ] Apply widget-specific rate limits (e.g., `"15 per minute"` for chat).

6. **Widget config endpoint (public)**:
    - [ ] `GET /api/v1/widget/config` — accepts widget key, returns visual settings (color, position, welcome message, lead capture config). No auth required. This is how the widget loader fetches its configuration.

### Phase 3: Widget Management API (Dashboard)

1. **CRUD endpoints for business owners**:
    - [ ] `GET /api/v1/widget-admin/{workspace_id}` — get widget config (creates default if missing, generates key).
    - [ ] `PATCH /api/v1/widget-admin/{workspace_id}` — update visual settings, toggle lead capture.
    - [ ] `POST /api/v1/widget-admin/{workspace_id}/rotate-key` — generate new widget key, invalidate old one.
    - [ ] `POST /api/v1/widget-admin/{workspace_id}/toggle` — enable/disable widget (`is_active`).
    - [ ] All endpoints require `get_current_user` + workspace ownership validation.

2. **Register router**:
    - [ ] Add to `api.py` at prefix `/widget-admin`.

### Phase 4: Widget Frontend Bundle

1. **Widget project setup**:
    - [ ] Create `widget/` directory at project root (sibling to `frontend/` and `backend/`).
    - [ ] Initialize with `package.json`, `tsconfig.json`, `vite.config.ts` (library mode).
    - [ ] Dependencies: `preact`, `vite` (build only, no dev server needed).
    - [ ] Build target: single IIFE bundle (`lagent-widget.js`) + inlined CSS.

2. **Embed loader script**:
    - [ ] Create `widget/src/loader.ts` — the tiny script served at `/widget/embed.js?key=wk_xxx`:
        - Reads `key` from script tag's `src` URL or `data-key` attribute.
        - Fetches config from `GET /api/v1/widget/config?key=wk_xxx`.
        - Dynamically loads the full widget bundle.
        - Creates a Shadow DOM host `<div>` and mounts the widget inside.

3. **Widget components** (Preact):
    - [ ] `widget/src/components/Bubble.tsx` — floating launcher button with custom icon/color.
    - [ ] `widget/src/components/ChatPanel.tsx` — expandable chat panel with:
        - Header (powered by Lagent branding, close button).
        - Message list (user + assistant bubbles).
        - Input bar with send button.
    - [ ] `widget/src/components/LeadForm.tsx` — optional pre-chat form (email, name fields).
    - [ ] `widget/src/components/Message.tsx` — single message bubble with typing indicator support.

4. **Widget core logic**:
    - [ ] `widget/src/api.ts` — API client: `createSession()`, `streamChat()`, `getMessages()`.
    - [ ] `widget/src/state.ts` — simple state management (Preact signals or plain state): session token, messages, open/closed, lead captured.
    - [ ] SSE streaming consumer that appends tokens to the latest assistant message in real-time.

5. **Styling**:
    - [ ] All CSS is inlined in the bundle (no external stylesheets).
    - [ ] CSS custom properties driven by the widget config (color, position).
    - [ ] Responsive: works on mobile viewports (full-screen on small screens).

6. **Static file serving**:
    - [ ] Serve `embed.js` and `lagent-widget.js` from the backend as static files or via a CDN path.
    - [ ] Add a FastAPI `StaticFiles` mount or a dedicated route for `/widget/embed.js`.

### Phase 5: Lead Capture

1. **Lead model**:
    - [ ] Create `backend/app/models/lead.py`:
        - `id: int` (PK)
        - `workspace_id: int` (FK, indexed)
        - `session_id: str` (FK to session, nullable)
        - `email: str`
        - `name: Optional[str]`
        - `metadata: dict` (JSON — extra fields)
        - `created_at: datetime`
    - [ ] Alembic migration.

2. **Lead capture endpoint**:
    - [ ] `POST /api/v1/widget/lead` — accepts widget key + lead data, validates, stores.
    - [ ] Rate limit: `"5 per minute"` per IP.
    - [ ] Returns the session token (same flow as session creation — lead capture replaces anonymous session init when enabled).

3. **Lead listing for dashboard** (Phase 5 / Module 5 overlap):
    - [ ] `GET /api/v1/widget-admin/{workspace_id}/leads` — paginated lead list.
    - [ ] Deferred to Module 5 if needed.

### Phase 6: Dashboard UI for Widget Management

1. **Widget settings page**:
    - [ ] Create `frontend/src/pages/WidgetSettings.tsx`:
        - Visual preview of the widget (live preview with selected color/position).
        - Color picker, position toggle, welcome message editor.
        - Lead capture toggle + field configuration.
        - Embed code snippet (copy-to-clipboard).
        - Widget key display + rotate button.
    - [ ] Add route and sidebar navigation link in `Layout.tsx`.

## Verification Strategy

- **Isolation Test**: Create two workspaces with different widget keys. Verify that widget A cannot access widget B's knowledge base, agent config, or chat history.
- **CORS Test**: Attempt widget API calls from an unauthorized origin when `allowed_origins` is set — should be rejected.
- **Streaming Test**: Open the widget on a test HTML page, send a message, verify SSE tokens stream correctly.
- **Session Expiry Test**: Wait for JWT expiry, verify the widget gracefully creates a new session.
- **Rate Limit Test**: Rapidly send messages from the widget, verify rate limiting kicks in.
- **Shadow DOM Test**: Embed the widget on a page with conflicting CSS — verify no style leakage in either direction.
- **Lead Capture Test**: Enable lead capture, verify the form blocks chat until submitted, and the lead record appears in the DB.

## Definition of Done
- [ ] Business owners can copy a `<script>` tag from the dashboard and paste it into their website.
- [ ] The widget renders in a Shadow DOM, visually matching the owner's brand settings.
- [ ] End-users can chat with the AI agent and receive streamed responses with RAG-backed answers.
- [ ] Each widget is strictly isolated to its workspace — no cross-tenant data access.
- [ ] Lead capture form (when enabled) collects user info before allowing chat.
- [ ] Widget keys can be rotated from the dashboard.
- [ ] Widget-specific rate limiting prevents abuse.
