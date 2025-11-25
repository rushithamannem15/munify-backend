from sqlalchemy import Column, BigInteger, String, DateTime, Date, Text, Numeric, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship
from app.core.database import Base


class Project(Base):
    __tablename__ = "perdix_mp_projects"
    
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Organization Information
    organization_type = Column(String(255), nullable=False)
    organization_id = Column(String(255), nullable=False)
    
    # Project Identification
    project_reference_id = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False)
    department = Column(String(200), nullable=True)
    contact_person = Column(String(255), nullable=False)
    contact_person_designation = Column(String(255), nullable=True)
    contact_person_email = Column(String(255), nullable=True)
    contact_person_phone = Column(String(50), nullable=True)
    
    # Project Overview
    category = Column(String(100), nullable=True)  # Infrastructure, Sanitation, Water Supply, Transportation, Renewable Energy
    project_stage = Column(String(50), default='planning', nullable=True)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    
    # Location Information
    state = Column(String(255), nullable=True)
    city = Column(String(255), nullable=True)
    ward = Column(String(255), nullable=True)
    
    # Financial Information
    total_project_cost = Column(Numeric(15, 2), nullable=True)
    funding_requirement = Column(Numeric(15, 2), nullable=False)
    already_secured_funds = Column(Numeric(15, 2), default=0, nullable=True)
    commitment_gap = Column(Numeric(15, 2), nullable=True)  # Generated column - read-only
    currency = Column(String(10), default='INR', nullable=True)
    
    # Fundraising Timeline
    fundraising_start_date = Column(TIMESTAMP(timezone=True), nullable=True)
    fundraising_end_date = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Credit & Rating
    municipality_credit_rating = Column(String(20), nullable=True)
    municipality_credit_score = Column(Numeric(5, 2), nullable=True)
    
    # Status & Workflow
    status = Column(String(50), default='draft', nullable=True)
    visibility = Column(String(50), default='private', nullable=True)
    
    # Calculated Fields
    funding_raised = Column(Numeric(15, 2), default=0, nullable=True)
    funding_percentage = Column(Numeric(5, 2), nullable=True)  # Generated column - read-only
    
    # Source & Audit
    approved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    approved_by = Column(String(255), nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(255), nullable=True)
    
    # Relationships
    rejection_history = relationship("ProjectRejectionHistory", back_populates="project", cascade="all, delete-orphan")
    
    # Add check constraints
    __table_args__ = (
        CheckConstraint("project_stage IN ('planning', 'initiated', 'in_progress')", name="check_project_stage"),
        CheckConstraint(
            "status IN ('draft', 'pending_validation', 'active', 'funding_completed', 'closed', 'rejected')",
            name="check_status"
        ),
        CheckConstraint("visibility IN ('private', 'public')", name="check_visibility"),
    )

