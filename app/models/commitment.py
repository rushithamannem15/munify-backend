from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    Numeric,
    Integer,
    CheckConstraint,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Commitment(Base):
    __tablename__ = "perdix_mp_commitments"

    id = Column(BigInteger, primary_key=True, index=True)

    # Reference to project using project_reference_id
    project_id = Column(
        String(255),
        ForeignKey("perdix_mp_projects.project_reference_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Lender / organization details
    organization_type = Column(String(255), nullable=False)
    organization_id = Column(String(255), nullable=False)
    committed_by = Column(String(255), nullable=False)

    # Commitment details
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=True)
    funding_mode = Column(String(50), nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=True)
    tenure_months = Column(Integer, nullable=True)

    # Terms & conditions
    terms_conditions_text = Column(Text, nullable=True)

    # Status & workflow
    status = Column(String(50), default="under_review", nullable=False)

    # Approval
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    rejection_notes = Column(Text, nullable=True)

    # Acknowledgment
    acknowledgment_receipt_url = Column(String(500), nullable=True)
    acknowledgment_generated_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Tracking
    update_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=True
    )
    created_by = Column(String(255), nullable=True)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )
    updated_by = Column(String(255), nullable=True)

    # Relationships
    project = relationship(
        "Project",
        foreign_keys=[project_id],
        primaryjoin="Commitment.project_id == Project.project_reference_id",
        viewonly=True,
    )
    history = relationship(
        "CommitmentHistory",
        back_populates="commitment",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "funding_mode IN ('loan', 'grant', 'csr')",
            name="check_commitment_funding_mode",
        ),
        CheckConstraint(
            "status IN ('under_review', 'approved', 'rejected', 'withdrawn', 'funded', 'completed')",
            name="check_commitment_status",
        ),
    )



