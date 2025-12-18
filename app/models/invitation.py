from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Invitation(Base):
    """
    ORM model for invitations mapped to the new Perdix schema table `perdix_mp_invites`.

    IMPORTANT:
    - Attribute names are kept backward compatible with the old model
      (e.g. `full_name`, `organization_type_id`, `expiry`) so that
      existing Pydantic schemas and service code can continue to use
      the same attribute names, while the underlying database columns
      use the new Perdix naming.
    """

    __tablename__ = "perdix_mp_invites"

    # Core identifiers and user info
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    mobile_number = Column(String(20), nullable=False)
    user_id = Column(String(255), nullable=False)
    # Maps to DB column `user_name`
    full_name = Column("user_name", String(200), nullable=False)

    # Organization / role information
    organization_id = Column(String(255), nullable=False)
    # Maps to DB column `organization_type`
    organization_type_id = Column("organization_type", String(50), nullable=False)
    role_id = Column(String(255), nullable=False)
    role_name = Column(String(100), nullable=False)

    # Audit / status fields
    invited_by = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, server_default="P")
    # Maps to DB column `expires_at`
    expiry = Column("expires_at", DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    resend_count = Column(Integer, nullable=False, server_default="0")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(255), nullable=True)

