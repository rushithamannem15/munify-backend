from sqlalchemy import Column, BigInteger, String, Text, Integer, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProjectRejectionHistory(Base):
    __tablename__ = "perdix_mp_project_rejection_history"
    
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Foreign key to project
    project_id = Column(BigInteger, ForeignKey("perdix_mp_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Rejection details
    rejected_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    rejected_by = Column(String(255), nullable=False)
    rejection_note = Column(Text, nullable=False)
    
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=True)
    
    # Relationship
    project = relationship("Project", back_populates="rejection_history")

