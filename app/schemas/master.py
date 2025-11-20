from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class ProjectCategoryMasterResponse(BaseModel):
    id: int
    value: str
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ProjectStageMasterResponse(BaseModel):
    id: int
    value: str
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class MasterListResponse(BaseModel):
    status: str
    message: str
    data: list
    
    model_config = ConfigDict(from_attributes=True)

