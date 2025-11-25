from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ProjectFavoriteCreate(BaseModel):
    project_reference_id: str = Field(..., description="Project reference ID to favorite")
    organization_id: str = Field(..., description="Organization ID")
    user_id: str = Field(..., description="User ID who is favoriting the project")
    created_by: Optional[str] = Field(None, max_length=255, description="User who created the favorite")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectFavoriteUpdate(BaseModel):
    updated_by: Optional[str] = Field(None, max_length=255, description="User who updated the favorite")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectFavoriteResponse(BaseModel):
    id: int
    project_reference_id: str
    organization_id: str
    user_id: str
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

