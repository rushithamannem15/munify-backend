from sqlalchemy import Column, BigInteger, String, ForeignKey, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship
from app.core.database import Base


class RoleOrgSubmenuMapping(Base):
    """
    Role and Organization Type to Submenu Mapping table.
    Maps which submenus are accessible to which roles and organization types.
    """
    __tablename__ = "perdix_mp_role_org_submenu_mapping"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    role_id = Column(BigInteger, nullable=False, index=True)  # References perdix_mp_roles_master.id (external Perdix table, no FK constraint)
    org_type = Column(String(50), nullable=False, index=True)  # Organization type: 'municipality', 'lender', 'admin', 'government'
    submenu_id = Column(BigInteger, ForeignKey("perdix_mp_submenu_master.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False, server_default='A')  # 'A' = Active, 'I' = Inactive (for soft-delete capability)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String(255), nullable=True)
    
    # Relationship to submenu
    submenu = relationship("SubmenuMaster", back_populates="role_org_mappings")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('role_id', 'org_type', 'submenu_id', name='uq_role_org_submenu_mapping'),
        CheckConstraint("org_type IN ('municipality', 'lender', 'munify', 'government')", name="check_org_type"),
        CheckConstraint("status IN ('A', 'I')", name="check_mapping_status"),
        Index('idx_role_org_type', 'role_id', 'org_type'),  # Composite index for faster queries
    )

