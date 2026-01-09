from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.fee_configuration import (
    FeeConfigurationCreate,
    FeeConfigurationUpdate,
    FeeConfigurationResponse,
)
from app.services.fee_configuration_service import FeeConfigurationService
from app.core.logging import get_logger

logger = get_logger("api.fee_configurations")

router = APIRouter()


@router.get("/{fee_config_id}", response_model=dict, status_code=status.HTTP_200_OK)
def get_fee_configuration(
    fee_config_id: int,
    db: Session = Depends(get_db),
):
    """Get fee configuration by ID"""
    try:
        service = FeeConfigurationService(db)
        fee_config = service.get_fee_configuration_by_id(fee_config_id)
        fee_config_response = FeeConfigurationResponse.model_validate(fee_config)
        return {
            "status": "success",
            "message": "Fee configuration fetched successfully",
            "data": fee_config_response
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching fee configuration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch fee configuration: {str(e)}"
        )


@router.get("/organization/{organization_id}", response_model=dict, status_code=status.HTTP_200_OK)
def get_fee_configuration_by_organization_id(
    organization_id: str,
    db: Session = Depends(get_db),
):
    """Get fee configuration by organization ID"""
    try:
        service = FeeConfigurationService(db)
        fee_config = service.get_fee_configuration_by_organization_id(organization_id)
        fee_config_response = FeeConfigurationResponse.model_validate(fee_config)
        return {
            "status": "success",
            "message": "Fee configuration fetched successfully",
            "data": fee_config_response
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching fee configuration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch fee configuration: {str(e)}"
        )


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_fee_configuration(
    fee_config_data: FeeConfigurationCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new fee configuration for an organization.
    
    Fee configurations are set by Munify Admin at the organization level.
    Default exemptions are automatically applied based on organization_type:
    - Admins: Fully exempt from subscription
    - Govt/NIUA: Exempt from subscription and listing fees
    - Lenders: Subscription fee may apply
    - Municipalities: Listing fee (on posting) + Success fee (on closure)
    """
    try:
        service = FeeConfigurationService(db)
        fee_config = service.create_fee_configuration(fee_config_data)
        fee_config_response = FeeConfigurationResponse.model_validate(fee_config)
        return {
            "status": "success",
            "message": "Fee configuration created successfully",
            "data": fee_config_response
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating fee configuration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create fee configuration: {str(e)}"
        )


@router.put("/{fee_config_id}", response_model=dict, status_code=status.HTTP_200_OK)
def update_fee_configuration(
    fee_config_id: int,
    fee_config_data: FeeConfigurationUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an existing fee configuration.
    
    Organization-type-specific update restrictions:
    - Lender: Only subscription_fee_annual, subscription_fee_currency, subscription_period_months can be updated
    - Municipality: Only listing_fee_percentage, success_fee_percentage can be updated
    - Admin/Govt/NIUA: No updates allowed (returns 403 Forbidden)
    
    Note: organization_type and organization_id cannot be changed after creation.
    """
    try:
        # Log the incoming data for debugging
        logger.info(f"Received update request for fee_config_id: {fee_config_id}")
        logger.info(f"Update data received: {fee_config_data.model_dump(exclude_unset=True)}")
        
        service = FeeConfigurationService(db)
        fee_config = service.update_fee_configuration(fee_config_id, fee_config_data)
        fee_config_response = FeeConfigurationResponse.model_validate(fee_config)
        
        # Log the response data
        logger.info(f"Fee configuration response - exemption reasons: subscription={fee_config_response.subscription_fee_exemption_reason}, listing={fee_config_response.listing_fee_exemption_reason}, success={fee_config_response.success_fee_exemption_reason}")
        
        return {
            "status": "success",
            "message": "Fee configuration updated successfully",
            "data": fee_config_response
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating fee configuration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update fee configuration: {str(e)}"
        )

