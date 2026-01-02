from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.core.database import Base


class StateMunicipalityMapping(Base):
    __tablename__ = "perdix_mp_state_municipality_mapping"
    
    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(255), nullable=False, index=True)
    municipality = Column(String(500), nullable=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(255), nullable=True)

