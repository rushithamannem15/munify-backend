from sqlalchemy import Column, BigInteger, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, JSONB
from sqlalchemy.sql import func
from sqlalchemy import text
from app.core.database import Base


class ProjectNote(Base):
    __tablename__ = "perdix_mp_project_notes"

    id = Column(BigInteger, primary_key=True, index=True)

    # Foreign key to project (references project_reference_id)
    project_reference_id = Column(
        String(255),
        ForeignKey("perdix_mp_projects.project_reference_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Organization information
    organization_id = Column(String(255), nullable=False, index=True)

    # Note details
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    tags = Column(JSONB, server_default=text("'[]'::jsonb"))

    # Audit fields
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(255), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(255), nullable=True)


