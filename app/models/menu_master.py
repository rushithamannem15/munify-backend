from sqlalchemy import Column, BigInteger, String, Integer, Text, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship
from app.core.database import Base


class MenuMaster(Base):
    """
    Menu Master table for storing main menu items.
    Each menu can have multiple submenus.
    """
    __tablename__ = "perdix_mp_menu_master"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    menu_name = Column(String(255), nullable=False, unique=True)
    menu_icon = Column(String(255), nullable=True)  # Icon name or path
    description = Column(Text, nullable=True)  # Optional description for the menu
    display_order = Column(Integer, nullable=True)  # For frontend menu ordering
    status = Column(String(50), nullable=False, server_default='A')  # 'A' = Active, 'I' = Inactive
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String(255), nullable=True)
    
    # Relationship to submenus
    submenus = relationship("SubmenuMaster", back_populates="menu", cascade="all, delete-orphan")
    
    # Check constraint for status
    __table_args__ = (
        CheckConstraint("status IN ('A', 'I')", name="check_menu_status"),
    )

