---
description: Create a robust implementation plan via clarification questions and risk analysis
---

Create a detailed implementation plan for: ${input:goal-or-link-to-context:Describe the work item or paste a link/path with context}

Planning workflow (required):
1. Read these documents first:
   - [Product requirements](../../PRD.md)
   - [Engineering guideline](../../GUIDELINE.md)
2. Ask clarifying questions before planning when scope, constraints, or acceptance criteria are ambiguous.
   - Use focused questions to remove ambiguity.
   - Prefer asking about non-functional constraints too (security, performance, deadlines, dependencies).
3. Identify edge cases and failure modes explicitly.
4. Produce a plan that is implementation-ready and verifiable.

Output format (required):
1. Assessment (place this at the top)
   - Complexity: Low | Medium | High
   - Execution mode: Single pass | Multiple phases
   - Sub-agent feasibility: Yes/No
   - If yes, list independent workstreams that can be parallelized safely.
   - If no, explain key dependencies blocking parallelization.
2. Clarifications asked and assumptions made
3. Edge cases and risks
4. Step-by-step plan (ordered)
5. Verification strategy per major step
6. Dependencies and sequencing constraints
7. Definition of done

Plan storage rules:
- Save the final plan as a markdown file under `.agents/plans/{SEQUENCE}-{SLUG}.md` e.g. `.agents/plans/001-initial-setup.md`.
- If the user does not provide a file name, generate a clear slug-based name.
- Never place plan files outside `.agents/plans/`.

Quality bar:
- Keep steps concrete, testable, and small enough to execute reliably.
- Surface blockers early and propose mitigation options.
- Ensure the plan aligns with [Engineering guideline](../../GUIDELINE.md).