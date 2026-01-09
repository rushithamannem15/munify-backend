from sqlalchemy import Column, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.core.database import Base


class MasterTableList(Base):
    __tablename__ = "master_table_list"
    
    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(255), nullable=False, unique=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(255), nullable=True)

