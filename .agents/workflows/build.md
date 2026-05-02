---
description: Execute a plan from .agents/plans in strict order with verification
---

Execute this implementation plan: ${input:link-to-plan:Paste a workspace-relative markdown path under .agents/plans/}

Execution rules:
1. Validate the provided plan path.
2. The plan file must be inside `.agents/plans/`.
   - If it is not, stop and ask the user to move/create the plan in `.agents/plans/`.
3. Read [Engineering guideline](../../GUIDELINE.md) before making edits, and explicitly confirm you will follow them.
4. Execute plan steps in order, without skipping ahead. 
  - If plan has steps that can be parallelized, you may execute those concurrently using sub-agents, but only after completing any prerequisite steps.
5. After each meaningful code change, verify before proceeding:
   - Run relevant tests/lint/type-check when available.
   - Check for errors in changed files.
   - Fix regressions introduced by your change.
6. Continue until all plan items are completed or you are blocked.
7. After all steps are done (or you are blocked), update [PROGRESS.md](../../PROGRESS.md):
   - Mark completed steps with `[x]`, in-progress with `[-]`, and not-done with `[ ]`.
   - Add any relevant notes (blockers, decisions made, versions pinned, etc.).
   - This ensures anyone resuming work can start exactly where we left off.
8. End with:
   - Completed steps
   - Verification performed and outcomes
   - Any remaining blockers or follow-ups

Plan authoring rule:
- Any new plan you create during this workflow must be saved under `.agents/plans/`.