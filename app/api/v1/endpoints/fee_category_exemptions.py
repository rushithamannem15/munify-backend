"""
Fee Category Exemptions API Endpoints

Handles CRUD operations for fee category exemptions.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.fee_category_exemption_service import FeeCategoryExemptionService
from app.schemas.fee_category_exemption import (
    FeeCategoryExemptionCreate,
    FeeCategoryExemptionUpdate,
    FeeCategoryExemptionResponse,
    FeeCategoryExemptionListResponse
)
from app.core.logging import get_logger

logger = get_logger("api.fee_category_exemptions")

router = APIRouter()


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_fee_category_exemption(
    exemption_data: FeeCategoryExemptionCreate,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(None, alias="user_id", description="User ID who created the exemption")
):
    """
    Create a new fee category exemption.
    
    Request body fields:
    - project_category: Project category (e.g., 'Infrastructure', 'Sanitation', 'Water Supply')
    - is_listing_fee_exempt: Exempt from listing fee (default: false)
    - is_success_fee_exempt: Exempt from success fee (default: false)
    - exemption_reason: Reason for exemption (optional)
    
    Header:
    - user_id: User ID who created the exemption (optional)
    """
    try:
        service = FeeCategoryExemptionService(db)
        exemption = service.create_fee_category_exemption(exemption_data, created_by=user_id)
        
        return {
            "status": "success",
            "message": "Fee category exemption created successfully",
            "data": FeeCategoryExemptionResponse.model_validate(exemption).model_dump()
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error creating fee category exemption: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create fee category exemption: {str(exc)}"
        )


@router.get("/", response_model=FeeCategoryExemptionListResponse, status_code=status.HTTP_200_OK)
def get_fee_category_exemptions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db)
):
    """
    Get all fee category exemptions with pagination.
    
    Query parameters:
    - skip: Number of records to skip (default: 0)
    - limit: Maximum number of records to return (default: 100, max: 1000)
    - is_active: Filter by active status (optional)
    """
    try:
        service = FeeCategoryExemptionService(db)
        exemptions, total = service.get_all_fee_category_exemptions(
            skip=skip,
            limit=limit,
            is_active=is_active
        )
        
        return {
            "status": "success",
            "message": "Fee category exemptions fetched successfully",
            "data": [FeeCategoryExemptionResponse.model_validate(ex) for ex in exemptions],
            "total": total
        }
    except Exception as exc:
        logger.error(f"Error fetching fee category exemptions: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch fee category exemptions: {str(exc)}"
        )


@router.get("/{exemption_id}", response_model=dict, status_code=status.HTTP_200_OK)
def get_fee_category_exemption(
    exemption_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a fee category exemption by ID.
    
    Path parameters:
    - exemption_id: ID of the fee category exemption
    """
    try:
        service = FeeCategoryExemptionService(db)
        exemption = service.get_fee_category_exemption_by_id(exemption_id)
        
        return {
            "status": "success",
            "message": "Fee category exemption fetched successfully",
            "data": FeeCategoryExemptionResponse.model_validate(exemption).model_dump()
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching fee category exemption: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch fee category exemption: {str(exc)}"
        )


@router.get("/category/{project_category}", response_model=dict, status_code=status.HTTP_200_OK)
def get_fee_category_exemption_by_category(
    project_category: str,
    db: Session = Depends(get_db)
):
    """
    Get a fee category exemption by project category.
    
    Path parameters:
    - project_category: Project category name (e.g., 'Infrastructure', 'Sanitation')
    """
    try:
        service = FeeCategoryExemptionService(db)
        exemption = service.get_fee_category_exemption_by_category(project_category)
        
        return {
            "status": "success",
            "message": "Fee category exemption fetched successfully",
            "data": FeeCategoryExemptionResponse.model_validate(exemption).model_dump()
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching fee category exemption: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch fee category exemption: {str(exc)}"
        )


@router.put("/{exemption_id}", response_model=dict, status_code=status.HTTP_200_OK)
def update_fee_category_exemption(
    exemption_id: int,
    exemption_data: FeeCategoryExemptionUpdate,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(None, alias="user_id", description="User ID who updated the exemption")
):
    """
    Update a fee category exemption.
    
    Path parameters:
    - exemption_id: ID of the fee category exemption to update
    
    Request body fields (all optional):
    - is_listing_fee_exempt: Exempt from listing fee
    - is_success_fee_exempt: Exempt from success fee
    - exemption_reason: Reason for exemption
    - is_active: Active status
    
    Header:
    - user_id: User ID who updated the exemption (optional)
    """
    try:
        service = FeeCategoryExemptionService(db)
        exemption = service.update_fee_category_exemption(
            exemption_id,
            exemption_data,
            updated_by=user_id
        )
        
        return {
            "status": "success",
            "message": "Fee category exemption updated successfully",
            "data": FeeCategoryExemptionResponse.model_validate(exemption).model_dump()
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error updating fee category exemption: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update fee category exemption: {str(exc)}"
        )


@router.delete("/{exemption_id}", status_code=status.HTTP_200_OK)
def delete_fee_category_exemption(
    exemption_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a fee category exemption.
    
    Path parameters:
    - exemption_id: ID of the fee category exemption to delete
    
    Note: This is a hard delete operation. The record will be permanently removed from the database.
    """
    try:
        service = FeeCategoryExemptionService(db)
        service.delete_fee_category_exemption(exemption_id)
        
        return {
            "status": "success",
            "message": "Fee category exemption deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error deleting fee category exemption: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete fee category exemption: {str(exc)}"
        )

