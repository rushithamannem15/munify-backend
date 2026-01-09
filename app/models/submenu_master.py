from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship
from app.core.database import Base


class SubmenuMaster(Base):
    """
    Submenu Master table for storing submenu items.
    Each submenu belongs to a menu and can be mapped to roles and organization types.
    """
    __tablename__ = "perdix_mp_submenu_master"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    submenu_name = Column(String(255), nullable=False)
    submenu_icon = Column(String(255), nullable=True)  # Icon name or path
    route = Column(String(500), nullable=False)  # Frontend route path
    menu_id = Column(BigInteger, ForeignKey("perdix_mp_menu_master.id", ondelete="CASCADE"), nullable=False, index=True)
    display_order = Column(Integer, nullable=True)  # For ordering submenus within a menu
    status = Column(String(50), nullable=False, server_default='A')  # 'A' = Active, 'I' = Inactive
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String(255), nullable=True)
    
    # Relationships
    menu = relationship("MenuMaster", back_populates="submenus")
    role_org_mappings = relationship("RoleOrgSubmenuMapping", back_populates="submenu", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('submenu_name', name='uq_menu_submenu_name'),
        CheckConstraint("status IN ('A', 'I')", name="check_submenu_status"),
    )

