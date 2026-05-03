from pydantic import BaseModel, Field

class ManualKnowledgeCreate(BaseModel):
    """Schema for creating manual knowledge entry."""
    name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
