from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.core.database import Base


class FeeCategoryExemption(Base):
    __tablename__ = "perdix_mp_fee_category_exemptions"
    
    id = Column(Integer, primary_key=True, index=True)
    project_category = Column(String(100), nullable=False, unique=True, index=True)
    
    # Fee Exemptions
    is_listing_fee_exempt = Column(Boolean, default=False, nullable=False)
    is_success_fee_exempt = Column(Boolean, default=False, nullable=False)
    
    exemption_reason = Column(Text, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(255), nullable=True)

