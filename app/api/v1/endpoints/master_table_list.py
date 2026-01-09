from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.master_table_list_service import MasterTableListService
from app.schemas.master import MasterListResponse

router = APIRouter()


@router.get("/", response_model=MasterListResponse, status_code=status.HTTP_200_OK)
def get_all_master_table_names(db: Session = Depends(get_db)):
    """
    Get all master table names from the master_table_list table.
    
    Returns a list of all master tables with their IDs and table names.
    """
    service = MasterTableListService(db)
    data = service.get_all_table_names()
    return {
        "status": "success",
        "message": "Master table names fetched successfully",
        "data": data
    }

