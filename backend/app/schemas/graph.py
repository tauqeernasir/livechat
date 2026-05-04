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
