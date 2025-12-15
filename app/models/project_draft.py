from sqlalchemy import Column, BigInteger, String, DateTime, Date, Text, Numeric, Integer, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.core.database import Base


class ProjectDraft(Base):
    __tablename__ = "perdix_mp_project_drafts"
    
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Organization Information
    organization_type = Column(String(255), nullable=True)  # Nullable for drafts
    organization_id = Column(String(255), nullable=True)  # Nullable for drafts
    
    # Project Identification
    # Note: project_reference_id not generated for drafts - will be generated on submit
    title = Column(String(500), nullable=True)  # Nullable for drafts
    department = Column(String(200), nullable=True)
    contact_person = Column(String(255), nullable=True)  # Nullable for drafts
    contact_person_designation = Column(String(255), nullable=True)
    contact_person_email = Column(String(255), nullable=True)
    contact_person_phone = Column(String(50), nullable=True)
    
    # Project Overview
    category = Column(String(100), nullable=True)
    project_stage = Column(String(50), default='planning', nullable=True)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    funding_type = Column(String(100), nullable=True)  # e.g., loan, grant, equity
    commitment_allocation_days = Column(Integer, nullable=True)  # Number of days for commitment allocation
    minimum_commitment_fulfilment_percentage = Column(Numeric(5, 2), nullable=True)  # Minimum commitment fulfilment percentage
    mode_of_implementation = Column(String(100), nullable=True)  # e.g., PPP, Government, Private
    ownership = Column(String(100), nullable=True)  # e.g., Public, Private, Mixed
    
    # Location Information
    state = Column(String(255), nullable=True)
    city = Column(String(255), nullable=True)
    ward = Column(String(255), nullable=True)
    
    # Financial Information
    total_project_cost = Column(Numeric(15, 2), nullable=True)
    funding_requirement = Column(Numeric(15, 2), nullable=True)  # Nullable for drafts
    already_secured_funds = Column(Numeric(15, 2), default=0, nullable=True)
    commitment_gap = Column(Numeric(15, 2), nullable=True)
    currency = Column(String(10), default='INR', nullable=True)
    tenure = Column(Integer, nullable=True)  # Tenure in years
    cut_off_rate_percentage = Column(Numeric(5, 2), nullable=True)  # Cut-off rate percentage
    minimum_commitment_amount = Column(Numeric(15, 2), nullable=True)  # Minimum commitment amount
    conditions = Column(Text, nullable=True)  # Conditions for the project
    
    # Fundraising Timeline
    fundraising_start_date = Column(TIMESTAMP(timezone=True), nullable=True)
    fundraising_end_date = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Credit & Rating
    municipality_credit_rating = Column(String(20), nullable=True)
    municipality_credit_score = Column(Numeric(5, 2), nullable=True)
    
    # Status & Workflow (for draft tracking)
    visibility = Column(String(50), default='private', nullable=True)
    
    # Source & Audit
    approved_by = Column(String(255), nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Draft-specific fields
    last_saved_tab = Column(String(50), nullable=True)  # Track which tab was last saved: 'tab1', 'tab2', 'tab3'
    completion_percentage = Column(Numeric(5, 2), default=0, nullable=True)  # 0-100
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(255), nullable=True)  # User who created the draft
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(255), nullable=True)
    
    # Add check constraints
    __table_args__ = (
        CheckConstraint("project_stage IN ('planning', 'initiated', 'in_progress')", name="check_draft_project_stage"),
        CheckConstraint("visibility IN ('private', 'public')", name="check_draft_visibility"),
        CheckConstraint("completion_percentage >= 0 AND completion_percentage <= 100", name="check_completion_percentage"),
    )

