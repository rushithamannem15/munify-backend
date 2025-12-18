from decimal import Decimal
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr


class OrganizationCreate(BaseModel):
    bank_id: int = Field(..., alias="bankId")
    parent_branch_id: int = Field(..., alias="parentBranchId")
    branch_name: str = Field(..., alias="branchName")
    branch_mail_id: EmailStr = Field(..., alias="branchMailId")
    pin_code: int = Field(..., alias="pinCode")
    branch_open_date: str = Field(..., alias="branchOpenDate")
    cash_limit: int = Field(default=0, alias="cashLimit")
    finger_print_device_type: str = Field(default="SAGEM", alias="fingerPrintDeviceType")

    # Extra fields that are stored in our own DB (perdix_mp_org_details) and
    # are not part of the Perdix branch creation API payload.
    # These come from frontend based on organization type.
    org_type: Optional[str] = Field(None, alias="orgType")
    pan_number: Optional[str] = Field(None, alias="panNumber")
    gst_number: Optional[str] = Field(None, alias="gstNumber")
    state: Optional[str] = Field(None, alias="state")
    district: Optional[str] = Field(None, alias="district")
    type_of_lender: Optional[str] = Field(None, alias="lenderType")
    annual_budget_size: Optional[Decimal] = Field(
        None, alias="annualBudgetSize"
    )
    designation: Optional[str] = Field(None, alias="designation")
    created_by: Optional[str] = Field(None, alias="createdBy")
    updated_by: Optional[str] = Field(None, alias="updatedBy")

    class Config:
        populate_by_name = True


class OrganizationUpdate(BaseModel):
    bank_id: Optional[int] = Field(None, alias="bankId")
    parent_branch_id: Optional[int] = Field(None, alias="parentBranchId")
    branch_name: Optional[str] = Field(None, alias="branchName")
    branch_mail_id: Optional[EmailStr] = Field(None, alias="branchMailId")
    pin_code: Optional[int] = Field(None, alias="pinCode")
    branch_open_date: Optional[str] = Field(None, alias="branchOpenDate")
    cash_limit: Optional[int] = Field(None, alias="cashLimit")
    finger_print_device_type: Optional[str] = Field(None, alias="fingerPrintDeviceType")

    class Config:
        populate_by_name = True


class OrganizationResponse(BaseModel):
    status: str
    message: str
    data: dict

    class Config:
        from_attributes = True


class OrganizationListResponse(BaseModel):
    status: str
    message: str
    data: list
    total: int

    class Config:
        from_attributes = True


class PerdixOrgDetailResponse(BaseModel):
    """Response schema for PerdixOrgDetail"""
    id: int
    org_id: Optional[int] = Field(None, alias="orgId")
    pan_number: Optional[str] = Field(None, alias="panNumber")
    gst_number: Optional[str] = Field(None, alias="gstNumber")
    state: Optional[str] = None
    district: Optional[str] = None
    type_of_lender: Optional[str] = Field(None, alias="typeOfLender")
    annual_budget_size: Optional[Decimal] = Field(None, alias="annualBudgetSize")
    created_by: Optional[str] = Field(None, alias="createdBy")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")
    updated_by: Optional[str] = Field(None, alias="updatedBy")

    class Config:
        populate_by_name = True
        from_attributes = True