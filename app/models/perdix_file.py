from sqlalchemy import Column, BigInteger, String, Integer, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from app.core.database import Base


class PerdixFile(Base):
    __tablename__ = "perdix_mp_files"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    organization_id = Column(String(255), nullable=False)
    uploaded_by = Column(String(255), nullable=False)
    
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)  # bytes
    storage_path = Column(String(1000), nullable=False)  # S3/local path
    checksum = Column(String(64), nullable=False)  # SHA-256
    
    access_level = Column(String(50), default='private', nullable=False)
    download_count = Column(Integer, default=0, nullable=False)
    
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String(255), nullable=True)
    
    # Add check constraint for access_level
    __table_args__ = (
        CheckConstraint(
            "access_level IN ('public', 'restricted', 'private')",
            name='check_access_level'
        ),
    )

