from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class PerdixQueryRequest(BaseModel):
    """Schema for dynamic Perdix query requests"""
    identifier: str = Field(..., description="Query identifier (e.g., 'childBranch.list')")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Query parameters as key-value pairs")
    limit: int = Field(default=0, ge=0, description="Limit for pagination (0 = no limit)")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    skip_relogin: str = Field(default="yes", description="Skip relogin flag")

    class Config:
        json_schema_extra = {
            "example": {
                "identifier": "childBranch.list",
                "limit": 0,
                "offset": 0,
                "parameters": {
                    "parent_branch_id": 94
                },
                "skip_relogin": "yes"
            }
        }

