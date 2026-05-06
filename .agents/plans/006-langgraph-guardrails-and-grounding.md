# Plan: LangGraph Guardrails, Ambiguity Handling, and Grounded Scope Control

This plan outlines the steps to harden the LangGraph agent so it can safely handle ambiguous queries, enforce business scope, and provide concise, grounded responses with deterministic guardrails.

## Assessment
- **Complexity**: High
- **Execution mode**: Multiple phases (State/Policy -> Graph Routing -> Guardrail Enforcement -> Evaluation)
- **Sub-agent feasibility**: Yes
    - **Stream 1**: Graph architecture and routing changes.
    - **Stream 2**: Prompt and policy hardening.
    - **Stream 3**: Validation/evaluation suite for behavior guarantees.

## Clarifications & Assumptions
1.  **Scope Boundary**: The assistant should only answer questions related to company offerings (products, services, pricing, onboarding, account/support, and related policies).
2.  **KB as Source of Truth**: For company/service questions, knowledge base retrieval is mandatory before final answer generation.
3.  **Ambiguity Rule**: Low-confidence intent/relevance classification requires a clarification turn before final answering.
4.  **Guardrail Priority**: Deterministic graph routing and validators should take precedence over prompt-only behavior.
5.  **Fallback Safety**: On classifier/tool failures, prefer safe clarification/refusal behavior over fail-open unrestricted chat.

## Edge Cases & Risks
*   **Classifier Failure**: Current fail-open behavior can allow out-of-scope responses. We will switch to a safe fallback path.
*   **Empty/Weak KB Retrieval**: If retrieval returns no relevant context, the agent must acknowledge uncertainty and ask for clarification or suggest supported topics.
*   **Over-Restrictive Rejection**: Greetings or short follow-ups can be misclassified as irrelevant. We will preserve friendly onboarding behavior for normal conversation starters.
*   **Prompt Injection Attempts**: User attempts to bypass policy must be treated as untrusted input and blocked by input guardrails.
*   **Response Verbosity Drift**: Model outputs can become long even with prompt instructions. Output validation will enforce concise responses.

## Existing vs Required Improvements

### Already Implemented (Keep / Improve)
1.  **Relevance classification and reject route**:
    - [x] `classify_query -> chat/reject` structure exists in LangGraph.
    - [ ] Improve with confidence-threshold branching and safe error behavior.
2.  **Knowledge base tool exists**:
    - [x] `search_knowledge_base` tool is available to the agent.
    - [ ] Make retrieval deterministic and mandatory for company/service intents.
3.  **Prompt-level grounding and citation guidance**:
    - [x] System prompt instructs KB use and source citations.
    - [ ] Add hard output validation to enforce concise, grounded responses.
4.  **Out-of-scope rejection messaging**:
    - [x] Polite rejection node is implemented.
    - [ ] Expand with contextual redirection to supported business topics.

### Not Yet Implemented (Add)
1.  **Ambiguity-specific routing node** (clarify-first path).
2.  **Mandatory retrieval node for in-scope business intents**.
3.  **Input guardrail node** (prompt injection/scope abuse filtering).
4.  **Output guardrail node** (conciseness, grounding, citation presence).
5.  **Policy-aligned failure modes** for classifier/tool errors.
6.  **Automated evaluation coverage** for ambiguity, scope, and grounding requirements.

## Step-by-Step Plan

### Phase 1: State and Policy Foundation
1.  **Extend `GraphState` for policy routing**:
    - [x] Add fields for `needs_clarification`, `kb_required`, `kb_used`, `kb_result_count`, and `guardrail_status`.
2.  **Define confidence thresholds**:
    - [x] Introduce configuration for low/medium/high classifier confidence cutoffs.
3.  **Standardize policy decisions**:
    - [x] Add a small policy helper to map classifier output + confidence into routing actions.

### Phase 2: Graph Architecture Hardening
1.  **Add ambiguity/clarification node**:
    - [x] Route low-confidence or unclear requests to a `clarify_query` node.
    - [x] Keep clarification concise and explicitly tied to business scope.
2.  **Add retrieval gate node**:
    - [x] For in-scope intents (`support`, `sales`, `complaint`), force a `retrieve_kb` node before answer generation.
    - [x] Persist retrieval result metadata in graph state.
3.  **Refactor chat node responsibilities**:
    - [x] Keep `chat` focused on answer synthesis from validated state and retrieved context.
4.  **Update terminal routes**:
    - [x] Preserve `reject` for clearly irrelevant queries.
    - [x] Add a safe fallback path for classifier/tool exceptions.

### Phase 3: Input Guardrails
1.  **Implement input guardrail checks**:
    - [ ] Detect direct scope violations (irrelevant asks, broad non-business requests).
    - [ ] Detect policy bypass attempts (prompt injection patterns such as "ignore instructions").
2.  **Guardrail outcomes**:
    - [ ] Route blocked inputs to `reject` with clear, business-focused redirection.
    - [ ] Route borderline inputs to `clarify_query`.

### Phase 4: Output Guardrails
1.  **Implement output validator node**:
    - [ ] Enforce concise response limits (length/sentence cap).
    - [ ] Require grounding signals for business claims (citations or retrieved source references).
2.  **Handle validator failures**:
    - [ ] If output is verbose/ungrounded, run one constrained regeneration pass.
    - [ ] If still non-compliant, return a safe fallback response.

### Phase 5: Prompt and Tooling Alignment
1.  **Classifier prompt upgrades**:
    - [ ] Add explicit ambiguity criteria and examples for mixed-intent or underspecified user asks.
2.  **System prompt upgrades**:
    - [ ] Align instructions with deterministic routing (KB-first, concise responses, strict business scope).
3.  **Tool contract improvements**:
    - [ ] Ensure KB tool returns structured, source-aware payloads usable by output validator.

### Phase 6: Safety, Reliability, and Observability
1.  **Failure mode changes**:
    - [ ] Replace classifier fail-open behavior with safe clarification/refusal strategy.
2.  **Metrics/logging additions**:
    - [ ] Track guardrail trigger counts, clarification rate, rejection rate, KB-hit rate, and validator retries.
3.  **Trace annotations**:
    - [ ] Tag Langfuse traces with guardrail decisions and policy outcomes for auditability.

### Phase 7: Test and Evaluation Coverage
1.  **Scenario test matrix**:
    - [ ] Ambiguous in-scope query -> clarification path.
    - [ ] Clear in-scope query -> mandatory KB retrieval -> grounded answer.
    - [ ] Out-of-scope query -> rejection path.
    - [ ] Prompt-injection attempt -> blocked/refused.
    - [ ] Empty KB results -> safe fallback (no hallucination).
2.  **Regression checks**:
    - [ ] Ensure normal greetings and basic onboarding prompts are still accepted.
3.  **Evaluation harness update**:
    - [ ] Add scoring criteria for conciseness, grounding, and scope compliance.

## Verification Strategy
- **Behavioral Validation**: Run manual end-to-end chat scenarios for each policy branch (clarify, retrieve, reject, safe fallback).
- **Log Audit**: Confirm graph routes and guardrail decisions are visible with structured logging.
- **Grounding Audit**: Verify company/service responses consistently include KB-backed references.
- **Safety Audit**: Verify non-business and prompt-injection requests are refused or redirected.
- **Conciseness Audit**: Verify output validator consistently limits verbosity.

## Definition of Done
- [ ] Ambiguous queries are routed to clarification before answering.
- [ ] Company/service queries always go through KB retrieval before final response generation.
- [ ] Input and output guardrails are enforced by graph logic, not prompt text alone.
- [ ] Out-of-scope or irrelevant requests are consistently rejected with helpful redirection.
- [ ] Classifier/tool failure modes are safe (no unrestricted fail-open behavior).
- [ ] Evaluation suite includes ambiguity, grounding, and scope-compliance tests with passing thresholds.
