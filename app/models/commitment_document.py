from sqlalchemy import Column, BigInteger, String, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class CommitmentDocument(Base):
    __tablename__ = "perdix_mp_commitment_documents"
    
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Foreign key to commitment
    # NOTE: Schema shows varchar(255) but commitment.id is BIGINT.
    # Using BigInteger to match the actual foreign key reference.
    commitment_id = Column(
        BigInteger,
        ForeignKey("perdix_mp_commitments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Foreign key to file
    file_id = Column(
        BigInteger,
        ForeignKey("perdix_mp_files.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Document details
    document_type = Column(String(100), nullable=False)  # sanction_letter, approval_note, kyc, terms_sheet, due_diligence
    is_required = Column(Boolean, default=True, nullable=False)
    
    # Uploader information
    uploaded_by = Column(String(255), nullable=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(255), nullable=True)
    
    # Relationships
    file = relationship("PerdixFile", foreign_keys=[file_id])
    commitment = relationship("Commitment", foreign_keys=[commitment_id])
    
    # Add check constraint for document_type
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('sanction_letter', 'approval_note', 'kyc', 'terms_sheet', 'due_diligence')",
            name='check_commitment_document_type'
        ),
    )

