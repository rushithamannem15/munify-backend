from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from app.core.database import Base


class PerdixUserDetail(Base):
    __tablename__ = "perdix_mp_users_details"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    organization_name = Column(String(255), nullable=False)
    organization_type = Column(String(50), nullable=False)
    # Perdix user identifier (login). This is now nullable to allow
    # creating the local record before syncing with Perdix.
    user_id = Column(String(255), nullable=True, unique=True, index=True)
    user_role = Column(BigInteger, nullable=False)
    user_name = Column(String(200), nullable=True)
    user_email = Column(String(255), nullable=False)
    user_mobile_number = Column(String(20), nullable=True)
    designation = Column(String(100), nullable=True)
    registration_number = Column(String(100), nullable=True)
    is_tc_accepted = Column(Boolean, default=False, nullable=False)  # Note: PostgreSQL doesn't support & in column names, using is_tc_accepted
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    gstn_ulb_code = Column(String(50), nullable=True)
    annual_budget_size = Column(Numeric(15, 2), nullable=True)
    status = Column(String(50), nullable=True)
    is_mobile_verified = Column(Boolean, default=False, nullable=False)
    mobile_verified_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String(255), nullable=True)
    file_id = Column(BigInteger, ForeignKey("perdix_mp_files.id"), nullable=True)

