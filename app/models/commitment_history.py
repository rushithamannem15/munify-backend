from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    Numeric,
    Integer,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class CommitmentHistory(Base):
    __tablename__ = "perdix_mp_commitment_history"

    id = Column(BigInteger, primary_key=True, index=True)

    commitment_id = Column(
        BigInteger,
        ForeignKey("perdix_mp_commitments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = Column(
        String(255),
        ForeignKey("perdix_mp_projects.project_reference_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    organization_type = Column(String(255), nullable=False)
    organization_id = Column(String(255), nullable=False)
    committed_by = Column(String(255), nullable=False)

    amount = Column(Numeric(15, 2), nullable=True)
    funding_mode = Column(String(50), nullable=True)
    interest_rate = Column(Numeric(5, 2), nullable=True)
    tenure_months = Column(Integer, nullable=True)
    terms_conditions_text = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)

    action = Column(String(50), nullable=False)

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
    commitment = relationship("Commitment", back_populates="history")
    project = relationship(
        "Project",
        foreign_keys=[project_id],
        primaryjoin="CommitmentHistory.project_id == Project.project_reference_id",
        viewonly=True,
    )



