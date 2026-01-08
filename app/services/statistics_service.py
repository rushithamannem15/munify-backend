from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.core.logging import get_logger
from app.models.perdix_user_detail import PerdixUserDetail
from app.models.commitment import Commitment
from app.schemas.statistics import StatisticsResponse

logger = get_logger("services.statistics")


class StatisticsService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_landing_page_statistics(self) -> StatisticsResponse:
        """
        Get landing page statistics:
        - Total Municipal Corporations: Count from perdix_mp_users_details where organization_type = 'Municipality'
        - Total Projects Funded: Sum of amount from perdix_mp_commitments where status IN ('completed', 'approved', 'funded')
        - Total Active Lenders: Count from perdix_mp_users_details where organization_type = 'Lender'
        - Total Approved Commitment: Count of commitments from perdix_mp_commitments where status = 'approved'
        """
        logger.info("Fetching landing page statistics")
        
        try:
            # Count total municipal corporations
            total_municipal_corporations = (
                self.db.query(func.count(PerdixUserDetail.id))
                .filter(PerdixUserDetail.organization_type == "Municipality")
                .scalar() or 0
            )
            
            # Sum total amount of commitments (status: completed, approved, or funded)
            total_projects_funded = (
                self.db.query(func.coalesce(func.sum(Commitment.amount), Decimal('0')))
                .filter(Commitment.status.in_(["completed", "approved", "funded"]))
                .scalar() or Decimal('0')
            )
            
            # Count total active lenders
            total_active_lenders = (
                self.db.query(func.count(PerdixUserDetail.id))
                .filter(PerdixUserDetail.organization_type == "Lender")
                .scalar() or 0
            )
            
            # Count total approved commitments
            total_approved_commitment = (
                self.db.query(func.count(Commitment.id))
                .filter(Commitment.status == "approved")
                .scalar() or 0
            )
            
            logger.info(
                f"Statistics fetched: Municipalities={total_municipal_corporations}, "
                f"Projects Funded={total_projects_funded}, "
                f"Active Lenders={total_active_lenders}, "
                f"Approved Commitment={total_approved_commitment}"
            )
            
            return StatisticsResponse(
                total_municipal_corporations=total_municipal_corporations,
                total_projects_funded=total_projects_funded,
                total_active_lenders=total_active_lenders,
                total_approved_commitment=total_approved_commitment
            )
            
        except Exception as e:
            logger.error(f"Error fetching landing page statistics: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch landing page statistics: {str(e)}"
            )

