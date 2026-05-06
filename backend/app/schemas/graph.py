"""This file contains the graph schema for the application."""

from typing import Annotated, Literal, Optional

from langgraph.graph.message import add_messages
from pydantic import (
    BaseModel,
    Field,
)


class GraphState(BaseModel):
    """State definition for the LangGraph Agent/Workflow."""

    messages: Annotated[list, add_messages] = Field(
        default_factory=list, description="The messages in the conversation"
    )
    intent: Optional[Literal["support", "sales", "complaint", "irrelevant"]] = Field(
        default=None,
        description="Classifier intent label for the latest user message",
    )
    is_relevant: Optional[bool] = Field(
        default=None,
        description="Whether the latest user request is relevant to company products/services",
    )
    relevance_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Classifier confidence score in range [0, 1]",
    )
    classifier_reason: Optional[str] = Field(
        default=None,
        description="Short internal reason for classifier decision",
    )
    needs_clarification: bool = Field(
        default=False,
        description="Whether the latest user query needs a clarification turn before final answering",
    )
    kb_required: bool = Field(
        default=False,
        description="Whether KB retrieval is required for the current query before final answer synthesis",
    )
    kb_used: bool = Field(
        default=False,
        description="Whether a KB retrieval step was used during this turn",
    )
    kb_result_count: int = Field(
        default=0,
        ge=0,
        description="Number of KB results retrieved for the current turn",
    )
    kb_context: str = Field(
        default="",
        description="Formatted KB retrieval context used for final answer synthesis",
    )
    guardrail_status: Literal["clear", "clarification_needed", "rejected", "classifier_failed"] = Field(
        default="clear",
        description="Latest guardrail policy status for the turn",
    )


class QueryClassification(BaseModel):
    """Structured output for intent and relevancy classification."""

    intent: Literal["support", "sales", "complaint", "irrelevant"] = Field(
        ...,
        description="Best-fit intent label for the latest user message",
    )
    is_relevant: bool = Field(
        ...,
        description="True if request is about company products/services",
    )
    kb_required: bool = Field(
        ...,
        description=(
            "True only if answering requires retrieving static knowledge base content "
            "(e.g. product docs, policies, FAQs). "
            "False when the query can be answered by a tool/API call (e.g. order lookup, account details) "
            "or from conversation context alone."
        ),
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the classification",
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="One short reason for internal logs/routing",
    )
