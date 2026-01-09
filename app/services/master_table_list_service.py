from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.logging import get_logger
from app.models.master_table_list import MasterTableList
from app.schemas.master import MasterTableListResponse

logger = get_logger("services.master_table_list")


class MasterTableListService:
    """Service for operations on master table list"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_table_names(self) -> List[Dict[str, Any]]:
        """
        Get all master table names from the master_table_list table.
        
        Returns:
            List of master table records as dictionaries
        """
        try:
            records = self.db.query(MasterTableList).order_by(MasterTableList.id).all()
            return [MasterTableListResponse.model_validate(record).model_dump() for record in records]
        except Exception as e:
            logger.error(f"Error fetching master table names: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch master table names: {str(e)}"
            )

