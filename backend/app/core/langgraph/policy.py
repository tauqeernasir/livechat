"""Policy helpers for intent/relevance and confidence-based routing decisions."""

from dataclasses import dataclass
from typing import Literal


InScopeIntent = Literal["support", "sales", "complaint", "irrelevant"]
GuardrailStatus = Literal["clear", "clarification_needed", "rejected", "classifier_failed"]


@dataclass(frozen=True)
class QueryPolicyDecision:
    """Policy decision for the latest classified user turn."""

    route: Literal["chat", "reject"]
    needs_clarification: bool
    guardrail_status: GuardrailStatus


def evaluate_query_policy(
    *,
    intent: InScopeIntent,
    is_relevant: bool,
    confidence: float,
    low_threshold: float,
    medium_threshold: float,
) -> QueryPolicyDecision:
    """Map classifier output and confidence into a policy decision.

    Phase 1 only computes policy metadata while preserving existing graph routes
    (`chat` and `reject`). Clarification/retrieval nodes are introduced later.
    """
    normalized_intent: InScopeIntent = "irrelevant" if not is_relevant else intent

    if normalized_intent == "irrelevant":
        return QueryPolicyDecision(
            route="reject",
            needs_clarification=False,
            guardrail_status="rejected",
        )

    needs_clarification = confidence < low_threshold

    return QueryPolicyDecision(
        route="chat",
        needs_clarification=needs_clarification,
        guardrail_status="clarification_needed" if needs_clarification else "clear",
    )
