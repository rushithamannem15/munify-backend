from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from decimal import Decimal
from datetime import date, datetime


class ProjectDraftCreate(BaseModel):
    """Schema for creating a new project draft - all fields optional"""
    project_reference_id: Optional[str] = Field(None, description="Project reference ID (auto-generated if not provided)")
    organization_type: Optional[str] = Field(None, description="Type of organization")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    title: Optional[str] = Field(None, max_length=500, description="Project title")
    department: Optional[str] = Field(None, max_length=200, description="Department name")
    contact_person: Optional[str] = Field(None, max_length=255, description="Contact person name")
    contact_person_designation: Optional[str] = Field(None, max_length=255, description="Contact person designation")
    contact_person_email: Optional[str] = Field(None, max_length=255, description="Contact person email")
    contact_person_phone: Optional[str] = Field(None, max_length=50, description="Contact person phone")
    category: Optional[str] = Field(None, max_length=100, description="Project category")
    project_stage: Optional[str] = Field('planning', description="Project stage: planning, initiated, in_progress")
    description: Optional[str] = Field(None, description="Project description")
    start_date: Optional[date] = Field(None, description="Project start date")
    end_date: Optional[date] = Field(None, description="Project end date")
    funding_type: Optional[str] = Field(None, max_length=100, description="Funding type: e.g., loan, grant, equity")
    commitment_allocation_days: Optional[int] = Field(None, description="Number of days for commitment allocation")
    minimum_commitment_fulfilment_percentage: Optional[Decimal] = Field(None, description="Minimum commitment fulfilment percentage")
    mode_of_implementation: Optional[str] = Field(None, max_length=100, description="Mode of implementation: e.g., PPP, Government, Private")
    ownership: Optional[str] = Field(None, max_length=100, description="Ownership: e.g., Public, Private, Mixed")
    state: Optional[str] = Field(None, max_length=255, description="State")
    city: Optional[str] = Field(None, max_length=255, description="City")
    ward: Optional[str] = Field(None, max_length=255, description="Ward")
    total_project_cost: Optional[Decimal] = Field(None, description="Total project cost")
    funding_requirement: Optional[Decimal] = Field(None, description="Funding requirement amount")
    already_secured_funds: Optional[Decimal] = Field(0, description="Already secured funds")
    commitment_gap: Optional[Decimal] = Field(None, description="Commitment gap amount")
    currency: Optional[str] = Field('INR', max_length=10, description="Currency code")
    tenure: Optional[int] = Field(None, description="Tenure in years")
    cut_off_rate_percentage: Optional[Decimal] = Field(None, description="Cut-off rate percentage")
    minimum_commitment_amount: Optional[Decimal] = Field(None, description="Minimum commitment amount")
    conditions: Optional[str] = Field(None, description="Conditions for the project")
    fundraising_start_date: Optional[datetime] = Field(None, description="Fundraising start date")
    fundraising_end_date: Optional[datetime] = Field(None, description="Fundraising end date")
    municipality_credit_rating: Optional[str] = Field(None, max_length=20, description="Municipality credit rating")
    municipality_credit_score: Optional[Decimal] = Field(None, description="Municipality credit score")
    visibility: Optional[str] = Field('private', description="Project visibility: private or public")
    approved_by: Optional[str] = Field(None, max_length=255, description="User who approved the project")
    admin_notes: Optional[str] = Field(None, description="Administrative notes")
    last_saved_tab: Optional[str] = Field(None, description="Last saved tab: tab1, tab2, or tab3")
    created_by: Optional[str] = Field(None, max_length=255, description="User who created the draft")
    model_config = ConfigDict(from_attributes=True)


class ProjectDraftUpdate(BaseModel):
    """Schema for updating a project draft - all fields optional"""
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
    funding_type: Optional[str] = Field(None, max_length=100, description="Funding type: e.g., loan, grant, equity")
    commitment_gap: Optional[Decimal] = Field(None, description="Commitment gap amount")
    commitment_allocation_days: Optional[int] = Field(None, description="Number of days for commitment allocation")
    minimum_commitment_fulfilment_percentage: Optional[Decimal] = Field(None, description="Minimum commitment fulfilment percentage")
    mode_of_implementation: Optional[str] = Field(None, max_length=100, description="Mode of implementation: e.g., PPP, Government, Private")
    ownership: Optional[str] = Field(None, max_length=100, description="Ownership: e.g., Public, Private, Mixed")
    state: Optional[str] = Field(None, max_length=255, description="State")
    city: Optional[str] = Field(None, max_length=255, description="City")
    ward: Optional[str] = Field(None, max_length=255, description="Ward")
    total_project_cost: Optional[Decimal] = Field(None, description="Total project cost")
    funding_requirement: Optional[Decimal] = Field(None, description="Funding requirement amount")
    already_secured_funds: Optional[Decimal] = Field(None, description="Already secured funds")
    currency: Optional[str] = Field(None, max_length=10, description="Currency code")
    tenure: Optional[int] = Field(None, description="Tenure in years")
    cut_off_rate_percentage: Optional[Decimal] = Field(None, description="Cut-off rate percentage")
    minimum_commitment_amount: Optional[Decimal] = Field(None, description="Minimum commitment amount")
    conditions: Optional[str] = Field(None, description="Conditions for the project")
    fundraising_start_date: Optional[datetime] = Field(None, description="Fundraising start date")
    fundraising_end_date: Optional[datetime] = Field(None, description="Fundraising end date")
    municipality_credit_rating: Optional[str] = Field(None, max_length=20, description="Municipality credit rating")
    municipality_credit_score: Optional[Decimal] = Field(None, description="Municipality credit score")
    visibility: Optional[str] = Field(None, description="Project visibility: private or public")
    approved_by: Optional[str] = Field(None, max_length=255, description="User who approved the project")
    admin_notes: Optional[str] = Field(None, description="Administrative notes")
    last_saved_tab: Optional[str] = Field(None, description="Last saved tab: tab1, tab2, or tab3")
    
    model_config = ConfigDict(from_attributes=True)


class ProjectDraftResponse(BaseModel):
    """Schema for project draft response"""
    id: int
    project_reference_id: Optional[str] = None
    organization_type: Optional[str] = None
    organization_id: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    contact_person: Optional[str] = None
    contact_person_designation: Optional[str] = None
    contact_person_email: Optional[str] = None
    contact_person_phone: Optional[str] = None
    category: Optional[str] = None
    project_stage: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    funding_type: Optional[str] = None
    commitment_allocation_days: Optional[int] = None
    minimum_commitment_fulfilment_percentage: Optional[Decimal] = None
    mode_of_implementation: Optional[str] = None
    ownership: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    ward: Optional[str] = None
    total_project_cost: Optional[Decimal] = None
    funding_requirement: Optional[Decimal] = None
    already_secured_funds: Optional[Decimal] = None
    commitment_gap: Optional[Decimal] = None
    currency: Optional[str] = None
    tenure: Optional[int] = None
    cut_off_rate_percentage: Optional[Decimal] = None
    minimum_commitment_amount: Optional[Decimal] = None
    conditions: Optional[str] = None
    fundraising_start_date: Optional[datetime] = None
    fundraising_end_date: Optional[datetime] = None
    municipality_credit_rating: Optional[str] = None
    municipality_credit_score: Optional[Decimal] = None
    visibility: Optional[str] = None
    approved_by: Optional[str] = None
    admin_notes: Optional[str] = None
    last_saved_tab: Optional[str] = None
    completion_percentage: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ProjectDraftListResponse(BaseModel):
    """Schema for listing project drafts"""
    status: str
    message: str
    data: list[ProjectDraftResponse]
    total: int

