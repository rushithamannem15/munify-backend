from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class CommitmentCreate(BaseModel):
    project_reference_id: str = Field(
        ..., description="Project reference ID for which the commitment is made"
    )
    organization_type: str = Field(..., description="Type of lender organization")
    organization_id: str = Field(..., description="Lender organization ID")
    committed_by: str = Field(..., description="User or entity who committed the funds")

    amount: Decimal = Field(..., description="Committed amount")
    currency: Optional[str] = Field("INR", description="Currency code (default: INR)")
    funding_mode: str = Field(
        ..., description="Funding mode: loan, grant, csr", pattern="^(loan|grant|csr)$"
    )
    interest_rate: Optional[Decimal] = Field(
        None, description="Interest rate (for loans)"
    )
    tenure_months: Optional[int] = Field(
        None, description="Tenure in months (for loans)"
    )
    terms_conditions_text: Optional[str] = Field(
        None, description="Free-text terms & conditions from lender"
    )

    created_by: Optional[str] = Field(
        None, description="User who created the commitment"
    )

    model_config = ConfigDict(from_attributes=True)


class CommitmentUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, description="Updated committed amount")
    currency: Optional[str] = Field(None, description="Currency code")
    funding_mode: Optional[str] = Field(
        None, description="Funding mode: loan, grant, csr"
    )
    interest_rate: Optional[Decimal] = Field(
        None, description="Interest rate (for loans)"
    )
    tenure_months: Optional[int] = Field(
        None, description="Tenure in months (for loans)"
    )
    terms_conditions_text: Optional[str] = Field(
        None, description="Updated terms & conditions"
    )
    updated_by: Optional[str] = Field(
        None, description="User who updated the commitment"
    )

    model_config = ConfigDict(from_attributes=True)


class CommitmentApproveRequest(BaseModel):
    approved_by: str = Field(..., description="User who approved the commitment")
    approval_notes: Optional[str] = Field(
        None, description="Optional notes for approval"
    )

    model_config = ConfigDict(from_attributes=True)


class CommitmentRejectRequest(BaseModel):
    approved_by: str = Field(..., description="User who rejected the commitment")
    rejection_reason: str = Field(..., description="High-level rejection reason")
    rejection_notes: Optional[str] = Field(
        None, description="Detailed rejection notes or comments"
    )

    model_config = ConfigDict(from_attributes=True)


class CommitmentStatusChangeRequest(BaseModel):
    updated_by: Optional[str] = Field(
        None, description="User performing the status change"
    )

    model_config = ConfigDict(from_attributes=True)


class CommitmentResponse(BaseModel):
    id: int
    project_id: str
    organization_type: str
    organization_id: str
    committed_by: str
    amount: Decimal
    currency: Optional[str] = None
    funding_mode: str
    interest_rate: Optional[Decimal] = None
    tenure_months: Optional[int] = None
    terms_conditions_text: Optional[str] = None
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    rejection_notes: Optional[str] = None
    acknowledgment_receipt_url: Optional[str] = None
    acknowledgment_generated_at: Optional[datetime] = None
    update_count: int
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CommitmentHistoryResponse(BaseModel):
    id: int
    commitment_id: int
    project_id: str
    organization_type: str
    organization_id: str
    committed_by: str
    amount: Optional[Decimal] = None
    funding_mode: Optional[str] = None
    interest_rate: Optional[Decimal] = None
    tenure_months: Optional[int] = None
    terms_conditions_text: Optional[str] = None
    status: Optional[str] = None
    action: str
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CommitmentListResponse(BaseModel):
    status: str
    message: str
    data: List[CommitmentResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)



