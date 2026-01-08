from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.statistics_service import StatisticsService
from app.schemas.statistics import StatisticsResponse

router = APIRouter()


@router.get(
    "/landing-page",
    response_model=dict,
    status_code=status.HTTP_200_OK
)
def get_landing_page_statistics(db: Session = Depends(get_db)):
    """
    Get landing page statistics including:
    - Total Municipal Corporations
    - Total Projects Funded
    - Total Active Lenders
    - Total Approved Commitment
    """
    try:
        service = StatisticsService(db)
        statistics = service.get_landing_page_statistics()
        
        return {
            "status": "success",
            "message": "Landing page statistics fetched successfully",
            "data": statistics
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch landing page statistics: {str(exc)}"
        )

