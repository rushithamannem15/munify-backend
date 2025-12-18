from sqlalchemy import Column, BigInteger, String, Numeric
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func

from app.core.database import Base


class PerdixOrgDetail(Base):
    """
    Local storage for additional organization (branch) details that are
    not part of the Perdix branch API payload.

    Backed by the `perdix_mp_org_details` table.
    """

    __tablename__ = "perdix_mp_org_details"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    # Perdix organization / branch identifier (if available from Perdix response)
    org_id = Column(BigInteger, nullable=True)

    # PAN and GST numbers
    # Matches DB column name `panNumber`
    pan_number = Column( String(50), nullable=True)
    gst_number = Column(String(50), nullable=True)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    # Matches DB column name `typeOfLender`
    type_of_lender = Column(String(100), nullable=True)
    annual_budget_size = Column(Numeric(15, 2), nullable=True)

    created_by = Column(String(255), nullable=True)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by = Column(String(255), nullable=True)


