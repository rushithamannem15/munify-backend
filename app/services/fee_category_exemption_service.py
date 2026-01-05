from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional, List
from app.models.fee_category_exemption import FeeCategoryExemption
from app.schemas.fee_category_exemption import (
    FeeCategoryExemptionCreate,
    FeeCategoryExemptionUpdate,
    FeeCategoryExemptionResponse
)
from app.core.logging import get_logger

logger = get_logger("services.fee_category_exemption")


class FeeCategoryExemptionService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_fee_category_exemption(
        self, 
        exemption_data: FeeCategoryExemptionCreate,
        created_by: Optional[str] = None
    ) -> FeeCategoryExemption:
        """Create a new fee category exemption"""
        logger.info(f"Creating fee category exemption for category: {exemption_data.project_category}")
        
        # Check if category exemption already exists
        existing = self.db.query(FeeCategoryExemption).filter(
            FeeCategoryExemption.project_category == exemption_data.project_category
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Fee category exemption for '{exemption_data.project_category}' already exists"
            )
        
        # Create new exemption
        exemption = FeeCategoryExemption(
            project_category=exemption_data.project_category,
            is_listing_fee_exempt=exemption_data.is_listing_fee_exempt,
            is_success_fee_exempt=exemption_data.is_success_fee_exempt,
            exemption_reason=exemption_data.exemption_reason,
            created_by=created_by
        )
        
        try:
            self.db.add(exemption)
            self.db.commit()
            self.db.refresh(exemption)
            logger.info(f"Fee category exemption {exemption.id} created successfully")
            return exemption
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating fee category exemption: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create fee category exemption: {str(e)}"
            )
    
    def get_fee_category_exemption_by_id(self, exemption_id: int) -> FeeCategoryExemption:
        """Get fee category exemption by ID"""
        exemption = self.db.query(FeeCategoryExemption).filter(
            FeeCategoryExemption.id == exemption_id
        ).first()
        
        if not exemption:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fee category exemption with ID {exemption_id} not found"
            )
        
        return exemption
    
    def get_fee_category_exemption_by_category(self, project_category: str) -> FeeCategoryExemption:
        """Get fee category exemption by project category"""
        exemption = self.db.query(FeeCategoryExemption).filter(
            FeeCategoryExemption.project_category == project_category
        ).first()
        
        if not exemption:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fee category exemption for category '{project_category}' not found"
            )
        
        return exemption
    
    def get_all_fee_category_exemptions(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> tuple[List[FeeCategoryExemption], int]:
        """Get all fee category exemptions with pagination"""
        query = self.db.query(FeeCategoryExemption)
        
        # Filter by active status if provided
        if is_active is not None:
            query = query.filter(FeeCategoryExemption.is_active == is_active)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        exemptions = query.order_by(FeeCategoryExemption.project_category).offset(skip).limit(limit).all()
        
        return exemptions, total
    
    def update_fee_category_exemption(
        self,
        exemption_id: int,
        exemption_data: FeeCategoryExemptionUpdate,
        updated_by: Optional[str] = None
    ) -> FeeCategoryExemption:
        """Update a fee category exemption"""
        logger.info(f"Updating fee category exemption {exemption_id}")
        
        exemption = self.get_fee_category_exemption_by_id(exemption_id)
        
        # Update only provided fields
        update_data = exemption_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(exemption, field, value)
        
        # Set updated_by
        if updated_by:
            exemption.updated_by = updated_by
        
        try:
            self.db.commit()
            self.db.refresh(exemption)
            logger.info(f"Fee category exemption {exemption_id} updated successfully")
            return exemption
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating fee category exemption: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update fee category exemption: {str(e)}"
            )
    
    def delete_fee_category_exemption(self, exemption_id: int) -> None:
        """Delete a fee category exemption"""
        logger.info(f"Deleting fee category exemption {exemption_id}")
        
        exemption = self.get_fee_category_exemption_by_id(exemption_id)
        
        try:
            self.db.delete(exemption)
            self.db.commit()
            logger.info(f"Fee category exemption {exemption_id} deleted successfully")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting fee category exemption: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete fee category exemption: {str(e)}"
            )

