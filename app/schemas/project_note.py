from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime


class ProjectNoteCreate(BaseModel):
    project_reference_id: str = Field(..., description="Project reference ID")
    organization_id: str = Field(..., description="Organization ID")
    title: Optional[str] = Field(None, max_length=255, description="Note title")
    content: str = Field(..., description="Note content (max 5000 characters)")
    tags: Optional[List[Any]] = Field(default_factory=list, description="List of tags for the note")
    created_by: str = Field(..., max_length=255, description="User who created the note")

    model_config = ConfigDict(from_attributes=True)


class ProjectNoteResponse(BaseModel):
    id: int
    project_reference_id: str
    organization_id: str
    title: Optional[str] = None
    content: str
    tags: List[Any] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    created_by: str
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


