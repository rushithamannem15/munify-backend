from sqlalchemy import Column, BigInteger, String, DateTime, Text, Numeric, Integer, Boolean, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.core.database import Base


class FeeConfiguration(Base):
    __tablename__ = "perdix_mp_fee_configurations"
    
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Organization Information
    organization_type = Column(String(255), nullable=False)
    organization_id = Column(String(255), nullable=False, unique=True, index=True)
    
    # Subscription Fee (Annual)
    subscription_fee_annual = Column(Numeric(10, 2), server_default='0', nullable=False)
    subscription_fee_currency = Column(String(10), server_default="INR", nullable=False)
    is_subscription_applicable = Column(Boolean, server_default='false', nullable=False)
    subscription_period_months = Column(Integer, server_default='12', nullable=False)
    
    # Listing Fee (% of project funding, payable on posting)
    listing_fee_percentage = Column(Numeric(5, 2), server_default='0', nullable=False)
    listing_fee_fixed = Column(Numeric(10, 2), server_default='0', nullable=False)
    is_listing_fee_applicable = Column(Boolean, server_default='false', nullable=False)
    is_listing_fee_payable_on_posting = Column(Boolean, server_default='false', nullable=False)
    
    # Commitment Fee (Future use)
    commitment_fee_percentage = Column(Numeric(5, 2), server_default='0', nullable=False)
    commitment_fee_fixed = Column(Numeric(10, 2), server_default='0', nullable=False)
    is_commitment_fee_applicable = Column(Boolean, server_default='false', nullable=False)
    
    # Success Fee (Municipalities - on project closure/sanction)
    success_fee_percentage = Column(Numeric(5, 2), server_default='0', nullable=False)
    success_fee_fixed = Column(Numeric(10, 2), server_default='0', nullable=False)
    is_success_fee_applicable = Column(Boolean, server_default='false', nullable=False)
    is_success_fee_adjusted_against_listing_fee = Column(Boolean, server_default='false', nullable=False)
    
    # Granular Exemptions
    is_subscription_exempt = Column(Boolean, server_default='false', nullable=False)
    is_listing_fee_exempt = Column(Boolean, server_default='false', nullable=False)
    is_success_fee_exempt = Column(Boolean, server_default='false', nullable=False)
    subscription_fee_exemption_reason = Column(Text, nullable=True, comment="Reason for subscription fee exemption")
    listing_fee_exemption_reason = Column(Text, nullable=True, comment="Reason for listing fee exemption")
    success_fee_exemption_reason = Column(Text, nullable=True, comment="Reason for success fee exemption")
    
    # Status & Audit
    is_active = Column(Boolean, server_default='false', nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(255), nullable=True)
    
    # Add check constraints
    __table_args__ = (
        CheckConstraint(
            "organization_type IN ('Lender', 'Municipality', 'Admin', 'Govt', 'NIUA')",
            name="check_organization_type"
        ),
        CheckConstraint(
            "listing_fee_percentage >= 0 AND listing_fee_percentage <= 100",
            name="check_listing_fee_percentage"
        ),
        CheckConstraint(
            "success_fee_percentage >= 0 AND success_fee_percentage <= 100",
            name="check_success_fee_percentage"
        ),
    )

