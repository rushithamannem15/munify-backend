from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime
from app.schemas.commitment import CommitmentResponse


class ProjectCreate(BaseModel):
    organization_type: str = Field(..., description="Type of organization")
    organization_id: str = Field(..., description="Organization ID")
    title: str = Field(..., max_length=500, description="Project title")
    department: Optional[str] = Field(None, max_length=200, description="Department name")
    contact_person: str = Field(..., max_length=255, description="Contact person name")
    contact_person_designation: Optional[str] = Field(None, max_length=255, description="Contact person designation")
    contact_person_email: Optional[str] = Field(None, max_length=255, description="Contact person email")
    contact_person_phone: Optional[str] = Field(None, max_length=50, description="Contact person phone")
    category: Optional[str] = Field(None, max_length=100, description="Project category")
    project_stage: Optional[str] = Field('planning', description="Project stage: planning, initiated, in_progress")
    description: Optional[str] = Field(None, description="Project description")
    start_date: Optional[date] = Field(None, description="Project start date")
    end_date: Optional[date] = Field(None, description="Project end date")
    state: Optional[str] = Field(None, max_length=255, description="State")
    city: Optional[str] = Field(None, max_length=255, description="City")
    ward: Optional[str] = Field(None, max_length=255, description="Ward")
    total_project_cost: Optional[Decimal] = Field(None, description="Total project cost")
    funding_requirement: Decimal = Field(..., description="Funding requirement amount")
    already_secured_funds: Optional[Decimal] = Field(0, description="Already secured funds")
    commitment_gap: Optional[Decimal] = Field(None, description="Commitment gap amount")
    currency: Optional[str] = Field('INR', max_length=10, description="Currency code")
    fundraising_start_date: Optional[datetime] = Field(None, description="Fundraising start date")
    fundraising_end_date: Optional[datetime] = Field(None, description="Fundraising end date")
    municipality_credit_rating: Optional[str] = Field(None, max_length=20, description="Municipality credit rating")
    municipality_credit_score: Optional[Decimal] = Field(None, description="Municipality credit score")
    status: Optional[str] = Field('draft', description="Project status")
    visibility: Optional[str] = Field('private', description="Project visibility: private or public")
    approved_by: Optional[str] = Field(None, max_length=255, description="User who approved the project")
    admin_notes: Optional[str] = Field(None, description="Administrative notes")
    created_by: Optional[str] = Field(None, max_length=255, description="User who created the project")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectUpdate(BaseModel):
    organization_type: Optional[str] = Field(None, description="Type of organization")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    title: Optional[str] = Field(None, max_length=500, description="Project title")
    department: Optional[str] = Field(None, max_length=200, description="Department name")
    contact_person: Optional[str] = Field(None, max_length=255, description="Contact person name")
    contact_person_designation: Optional[str] = Field(None, max_length=255, description="Contact person designation")
    contact_person_email: Optional[str] = Field(None, max_length=255, description="Contact person email")
    contact_person_phone: Optional[str] = Field(None, max_length=50, description="Contact person phone")
    category: Optional[str] = Field(None, max_length=100, description="Project category")
    project_stage: Optional[str] = Field(None, description="Project stage: planning, initiated, in_progress")
    description: Optional[str] = Field(None, description="Project description")
    start_date: Optional[date] = Field(None, description="Project start date")
    end_date: Optional[date] = Field(None, description="Project end date")
    state: Optional[str] = Field(None, max_length=255, description="State")
    city: Optional[str] = Field(None, max_length=255, description="City")
    ward: Optional[str] = Field(None, max_length=255, description="Ward")
    total_project_cost: Optional[Decimal] = Field(None, description="Total project cost")
    funding_requirement: Optional[Decimal] = Field(None, description="Funding requirement amount")
    already_secured_funds: Optional[Decimal] = Field(None, description="Already secured funds")
    currency: Optional[str] = Field(None, max_length=10, description="Currency code")
    fundraising_start_date: Optional[datetime] = Field(None, description="Fundraising start date")
    fundraising_end_date: Optional[datetime] = Field(None, description="Fundraising end date")
    municipality_credit_rating: Optional[str] = Field(None, max_length=20, description="Municipality credit rating")
    municipality_credit_score: Optional[Decimal] = Field(None, description="Municipality credit score")
    status: Optional[str] = Field(None, description="Project status")
    visibility: Optional[str] = Field(None, description="Project visibility: private or public")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    approved_by: Optional[str] = Field(None, max_length=255, description="User who approved the project")
    admin_notes: Optional[str] = Field(None, description="Administrative notes")
    updated_by: Optional[str] = Field(None, max_length=255, description="User who updated the project")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(BaseModel):
    id: int
    organization_type: str
    organization_id: str
    project_reference_id: str
    title: str
    department: Optional[str] = None
    contact_person: str
    contact_person_designation: Optional[str] = None
    contact_person_email: Optional[str] = None
    contact_person_phone: Optional[str] = None
    category: Optional[str] = None
    project_stage: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    state: Optional[str] = None
    city: Optional[str] = None
    ward: Optional[str] = None
    total_project_cost: Optional[Decimal] = None
    funding_requirement: Decimal
    already_secured_funds: Optional[Decimal] = None
    commitment_gap: Optional[Decimal] = None
    currency: Optional[str] = None
    fundraising_start_date: Optional[datetime] = None
    fundraising_end_date: Optional[datetime] = None
    municipality_credit_rating: Optional[str] = None
    municipality_credit_score: Optional[Decimal] = None
    status: Optional[str] = None
    visibility: Optional[str] = None
    funding_raised: Optional[Decimal] = None
    funding_percentage: Optional[Decimal] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    admin_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    is_favorite: Optional[bool] = Field(
        None,
        description="Indicates whether the project is favorited by the specified user (only set when user_id is provided)"
    )
    favorite_count: int = Field(
        0,
        description="Total number of users who have favorited this project"
    )
    commitment: Optional[CommitmentResponse] = Field(
        None,
        description="Commitment details for this project and committed_by (only set when requested in project reference API)",
    )
    
    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    status: str
    message: str
    data: list[ProjectResponse]
    total: int
    
    model_config = ConfigDict(from_attributes=True)


class ProjectApproveRequest(BaseModel):
    approved_by: str = Field(..., max_length=255, description="User who approved the project (mandatory)")
    admin_notes: Optional[str] = Field(None, description="Administrative notes (optional)")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectRejectRequest(BaseModel):
    reject_note: str = Field(..., description="Rejection note (mandatory)")
    approved_by: str = Field(..., max_length=255, description="User who rejected the project (mandatory)")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectResubmitRequest(BaseModel):
    """Schema for resubmitting a rejected project. Extends ProjectUpdate with optional resubmission notes."""
    # All fields from ProjectUpdate are optional
    organization_type: Optional[str] = Field(None, description="Type of organization")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    title: Optional[str] = Field(None, max_length=500, description="Project title")
    department: Optional[str] = Field(None, max_length=200, description="Department name")
    contact_person: Optional[str] = Field(None, max_length=255, description="Contact person name")
    contact_person_designation: Optional[str] = Field(None, max_length=255, description="Contact person designation")
    contact_person_email: Optional[str] = Field(None, max_length=255, description="Contact person email")
    contact_person_phone: Optional[str] = Field(None, max_length=50, description="Contact person phone")
    category: Optional[str] = Field(None, max_length=100, description="Project category")
    project_stage: Optional[str] = Field(None, description="Project stage: planning, initiated, in_progress")
    description: Optional[str] = Field(None, description="Project description")
    start_date: Optional[date] = Field(None, description="Project start date")
    end_date: Optional[date] = Field(None, description="Project end date")
    state: Optional[str] = Field(None, max_length=255, description="State")
    city: Optional[str] = Field(None, max_length=255, description="City")
    ward: Optional[str] = Field(None, max_length=255, description="Ward")
    total_project_cost: Optional[Decimal] = Field(None, description="Total project cost")
    funding_requirement: Optional[Decimal] = Field(None, description="Funding requirement amount")
    already_secured_funds: Optional[Decimal] = Field(None, description="Already secured funds")
    fundraising_start_date: Optional[datetime] = Field(None, description="Fundraising start date")
    fundraising_end_date: Optional[datetime] = Field(None, description="Fundraising end date")
    municipality_credit_rating: Optional[str] = Field(None, max_length=20, description="Municipality credit rating")
    municipality_credit_score: Optional[Decimal] = Field(None, description="Municipality credit score")
    visibility: Optional[str] = Field(None, description="Project visibility: private or public")
    resubmission_notes: Optional[str] = Field(None, description="Notes explaining what corrections were made (optional)")
    updated_by: Optional[str] = Field(None, max_length=255, description="User who resubmitted the project")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectRejectionHistoryResponse(BaseModel):
    """Schema for project rejection history response"""
    id: int
    project_id: int
    rejected_at: datetime
    rejected_by: str
    rejection_note: str
    resubmitted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ProjectCommitmentsSummaryResponse(BaseModel):
    """Schema for aggregated project commitments summary"""
    project_reference_id: str = Field(..., description="Project reference ID")
    project_title: str = Field(..., description="Project title")
    total_commitments_count: int = Field(..., description="Total number of commitments for this project")
    status_under_review: int = Field(0, description="Count of commitments under review")
    status_approved: int = Field(0, description="Count of approved commitments")
    status_rejected: int = Field(0, description="Count of rejected commitments")
    status_withdrawn: int = Field(0, description="Count of withdrawn commitments")
    total_amount_under_review: Decimal = Field(..., description="Total amount of commitments under review")
    best_deal_amount: Optional[Decimal] = Field(None, description="Best deal amount")
    best_deal_interest_rate: Optional[Decimal] = Field(None, description="Best deal interest rate (lowest for loans)")
    best_deal_funding_mode: Optional[str] = Field(None, description="Funding mode of best deal")
    latest_commitment_date: Optional[datetime] = Field(None, description="Date of the latest commitment")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectCommitmentsSummaryListResponse(BaseModel):
    """Schema for list of project commitments summary"""
    status: str
    message: str
    data: List[ProjectCommitmentsSummaryResponse]
    total: int
    
    model_config = ConfigDict(from_attributes=True)


class FullyFundedProjectResponse(BaseModel):
    """Schema for fully funded project with funding parameters"""
    # All project fields
    id: int
    organization_type: str
    organization_id: str
    project_reference_id: str
    title: str
    department: Optional[str] = None
    contact_person: str
    contact_person_designation: Optional[str] = None
    contact_person_email: Optional[str] = None
    contact_person_phone: Optional[str] = None
    category: Optional[str] = None
    project_stage: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    state: Optional[str] = None
    city: Optional[str] = None
    ward: Optional[str] = None
    total_project_cost: Optional[Decimal] = None
    funding_requirement: Decimal
    already_secured_funds: Optional[Decimal] = None
    commitment_gap: Optional[Decimal] = None
    currency: Optional[str] = None
    fundraising_start_date: Optional[datetime] = None
    fundraising_end_date: Optional[datetime] = None
    municipality_credit_rating: Optional[str] = None
    municipality_credit_score: Optional[Decimal] = None
    status: Optional[str] = None
    visibility: Optional[str] = None
    funding_raised: Optional[Decimal] = None
    funding_percentage: Optional[Decimal] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    admin_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    # Funding parameters from approved commitments
    average_interest_rate: Optional[Decimal] = Field(
        None,
        description="Average interest rate from approved commitments"
    )
    number_of_investors: int = Field(
        0,
        description="Number of investors (approved commitments count)"
    )
    
    model_config = ConfigDict(from_attributes=True)


class FullyFundedProjectListResponse(BaseModel):
    """Schema for list of fully funded projects"""
    status: str
    message: str
    data: List[FullyFundedProjectResponse]
    total: int
    
    model_config = ConfigDict(from_attributes=True)