from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime


class FeeCategoryExemptionCreate(BaseModel):
    """Schema for creating a fee category exemption"""
    project_category: str = Field(..., description="Project category (e.g., 'Infrastructure', 'Sanitation', 'Water Supply')")
    is_listing_fee_exempt: bool = Field(default=False, description="Exempt from listing fee")
    is_success_fee_exempt: bool = Field(default=False, description="Exempt from success fee")
    exemption_reason: Optional[str] = Field(None, description="Reason for exemption/override")


class FeeCategoryExemptionUpdate(BaseModel):
    """Schema for updating a fee category exemption"""
    is_listing_fee_exempt: Optional[bool] = Field(None, description="Exempt from listing fee")
    is_success_fee_exempt: Optional[bool] = Field(None, description="Exempt from success fee")
    exemption_reason: Optional[str] = Field(None, description="Reason for exemption/override")
    is_active: Optional[bool] = Field(None, description="Active status")


class FeeCategoryExemptionResponse(BaseModel):
    """Schema for fee category exemption response"""
    id: int
    project_category: str
    is_listing_fee_exempt: bool
    is_success_fee_exempt: bool
    exemption_reason: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class FeeCategoryExemptionListResponse(BaseModel):
    """Schema for list response"""
    status: str
    message: str
    data: list[FeeCategoryExemptionResponse]
    total: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

