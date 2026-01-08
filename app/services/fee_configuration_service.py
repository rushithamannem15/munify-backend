from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from decimal import Decimal
from typing import Optional

from app.models.fee_configuration import FeeConfiguration
from app.schemas.fee_configuration import FeeConfigurationCreate, FeeConfigurationUpdate
from app.core.logging import get_logger

logger = get_logger("services.fee_configuration")


class FeeConfigurationService:
    def __init__(self, db: Session):
        self.db = db
    
    def _validate_organization_type(self, organization_type: str):
        """Validate organization type"""
        allowed_types = ['Lender', 'Municipality', 'Admin', 'Govt', 'NIUA']
        if organization_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"organization_type must be one of: {', '.join(allowed_types)}"
            )
    
    def _validate_percentage(self, value: Optional[Decimal], field_name: str):
        """Validate percentage values are between 0 and 100"""
        if value is not None and (value < 0 or value > 100):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field_name} must be between 0 and 100"
            )
    
    def _validate_organization_id_unique(self, organization_id: str, exclude_id: Optional[int] = None):
        """Validate that organization_id is unique"""
        query = self.db.query(FeeConfiguration).filter(
            FeeConfiguration.organization_id == organization_id
        )
        if exclude_id:
            query = query.filter(FeeConfiguration.id != exclude_id)
        
        existing = query.first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Fee configuration already exists for organization_id: {organization_id}"
            )
    
    def _validate_organization_type_fields(self, fee_config_data: FeeConfigurationCreate):
        """Validate that only required fields are provided based on organization type"""
        org_type = fee_config_data.organization_type
        
        # Lender: Only subscription_fee_annual, subscription_fee_currency, subscription_period_months allowed
        if org_type == 'Lender':
            if fee_config_data.listing_fee_percentage is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="listing_fee_percentage is not applicable for Lender organization type"
                )
            if fee_config_data.success_fee_percentage is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="success_fee_percentage is not applicable for Lender organization type"
                )
            if fee_config_data.listing_fee_fixed is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="listing_fee_fixed is not applicable for Lender organization type"
                )
            if fee_config_data.success_fee_fixed is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="success_fee_fixed is not applicable for Lender organization type"
                )
        
        # Municipality: Only listing_fee_percentage, success_fee_percentage allowed
        elif org_type == 'Municipality':
            if fee_config_data.subscription_fee_annual is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="subscription_fee_annual is not applicable for Municipality organization type"
                )
            if fee_config_data.subscription_fee_currency is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="subscription_fee_currency is not applicable for Municipality organization type"
                )
            if fee_config_data.subscription_period_months is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="subscription_period_months is not applicable for Municipality organization type"
                )
        
        # Admin/Govt/NIUA: No fee input fields allowed
        elif org_type in ['Admin', 'Govt', 'NIUA']:
            if fee_config_data.subscription_fee_annual is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"subscription_fee_annual is not applicable for {org_type} organization type"
                )
            if fee_config_data.subscription_fee_currency is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"subscription_fee_currency is not applicable for {org_type} organization type"
                )
            if fee_config_data.subscription_period_months is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"subscription_period_months is not applicable for {org_type} organization type"
                )
            if fee_config_data.listing_fee_percentage is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"listing_fee_percentage is not applicable for {org_type} organization type"
                )
            if fee_config_data.success_fee_percentage is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"success_fee_percentage is not applicable for {org_type} organization type"
                )
    
    def _apply_organization_type_defaults(self, fee_config_dict: dict):
        """Apply default fee configurations based on organization type
        
        Sets all fields to False/default first, then applies organization-type-specific defaults.
        """
        org_type = fee_config_dict.get('organization_type')
        
        # Initialize all boolean fields to False and numeric fields to 0 (handle None values)
        if fee_config_dict.get('subscription_fee_annual') is None:
            fee_config_dict['subscription_fee_annual'] = Decimal('0')
        if fee_config_dict.get('subscription_fee_currency') is None:
            fee_config_dict['subscription_fee_currency'] = 'INR'
        fee_config_dict['is_subscription_applicable'] = False
        if fee_config_dict.get('subscription_period_months') is None:
            fee_config_dict['subscription_period_months'] = 12
        if fee_config_dict.get('listing_fee_percentage') is None:
            fee_config_dict['listing_fee_percentage'] = Decimal('0')
        if fee_config_dict.get('listing_fee_fixed') is None:
            fee_config_dict['listing_fee_fixed'] = Decimal('0')
        fee_config_dict['is_listing_fee_applicable'] = False
        fee_config_dict['is_listing_fee_payable_on_posting'] = False
        if fee_config_dict.get('commitment_fee_percentage') is None:
            fee_config_dict['commitment_fee_percentage'] = Decimal('0')
        if fee_config_dict.get('commitment_fee_fixed') is None:
            fee_config_dict['commitment_fee_fixed'] = Decimal('0')
        fee_config_dict['is_commitment_fee_applicable'] = False
        if fee_config_dict.get('success_fee_percentage') is None:
            fee_config_dict['success_fee_percentage'] = Decimal('0')
        if fee_config_dict.get('success_fee_fixed') is None:
            fee_config_dict['success_fee_fixed'] = Decimal('0')
        fee_config_dict['is_success_fee_applicable'] = False
        fee_config_dict['is_success_fee_adjusted_against_listing_fee'] = False
        fee_config_dict['is_subscription_exempt'] = False
        fee_config_dict['is_listing_fee_exempt'] = False
        fee_config_dict['is_success_fee_exempt'] = False
        fee_config_dict['is_active'] = False
        
        # Lender: Set subscription fields and exemptions
        if org_type == 'Lender':
            fee_config_dict['is_subscription_applicable'] = True
            fee_config_dict['is_listing_fee_exempt'] = True
            fee_config_dict['is_success_fee_exempt'] = True
            fee_config_dict['is_active'] = True
        
        # Municipality: Set listing and success fee fields
        elif org_type == 'Municipality':
            fee_config_dict['is_listing_fee_applicable'] = True
            fee_config_dict['is_listing_fee_payable_on_posting'] = True
            fee_config_dict['is_success_fee_applicable'] = True
            fee_config_dict['is_subscription_exempt'] = True
            fee_config_dict['is_active'] = True
        
        # Admin/Govt/NIUA: Set exemptions
        elif org_type in ['Admin', 'Govt', 'NIUA']:
            fee_config_dict['is_subscription_exempt'] = True
            fee_config_dict['is_listing_fee_exempt'] = True
            fee_config_dict['is_success_fee_exempt'] = True
            # Set exemption reasons if not provided
            if org_type == 'Admin':
                if not fee_config_dict.get('subscription_fee_exemption_reason'):
                    fee_config_dict['subscription_fee_exemption_reason'] = "Admin user - fully exempt from subscription fee"
                if not fee_config_dict.get('listing_fee_exemption_reason'):
                    fee_config_dict['listing_fee_exemption_reason'] = "Admin user - fully exempt from listing fee"
                if not fee_config_dict.get('success_fee_exemption_reason'):
                    fee_config_dict['success_fee_exemption_reason'] = "Admin user - fully exempt from success fee"
            else:
                if not fee_config_dict.get('subscription_fee_exemption_reason'):
                    fee_config_dict['subscription_fee_exemption_reason'] = f"{org_type} invited user - exempt from subscription fee"
                if not fee_config_dict.get('listing_fee_exemption_reason'):
                    fee_config_dict['listing_fee_exemption_reason'] = f"{org_type} invited user - exempt from listing fee"
                if not fee_config_dict.get('success_fee_exemption_reason'):
                    fee_config_dict['success_fee_exemption_reason'] = f"{org_type} invited user - exempt from success fee"
    
    def create_fee_configuration(
        self, 
        fee_config_data: FeeConfigurationCreate,
        created_by: Optional[str] = None
    ) -> FeeConfiguration:
        """Create a new fee configuration
        
        Organization-type-specific requirements:
        - Lender: Input fields: subscription_fee_annual, subscription_fee_currency, subscription_period_months
                  Auto-set: is_subscription_applicable=True, is_listing_fee_exempt=True, is_success_fee_exempt=True, is_active=True
        - Municipality: Input fields: listing_fee_percentage, success_fee_percentage
                        Auto-set: is_listing_fee_applicable=True, is_listing_fee_payable_on_posting=True, is_success_fee_applicable=True, is_subscription_exempt=True, is_active=True
        - Admin/Govt/NIUA: No input fields required
                           Auto-set: is_subscription_exempt=True, is_listing_fee_exempt=True, is_success_fee_exempt=True
        
        All other fields are set to False/default values.
        """
        logger.info(f"Creating fee configuration for organization_id: {fee_config_data.organization_id}, type: {fee_config_data.organization_type}")
        
        # Validate organization type
        self._validate_organization_type(fee_config_data.organization_type)
        
        # Validate that only required fields are provided for the organization type
        self._validate_organization_type_fields(fee_config_data)
        
        # Convert to dict, apply organization type defaults, then recreate
        fee_config_dict = fee_config_data.model_dump()
        self._apply_organization_type_defaults(fee_config_dict)
        # Recreate the model with updated values
        fee_config_data = FeeConfigurationCreate(**fee_config_dict)
        
        # Validate percentages
        if fee_config_data.listing_fee_percentage is not None:
            self._validate_percentage(fee_config_data.listing_fee_percentage, "listing_fee_percentage")
        if fee_config_data.success_fee_percentage is not None:
            self._validate_percentage(fee_config_data.success_fee_percentage, "success_fee_percentage")
        
        # Validate organization_id uniqueness
        self._validate_organization_id_unique(fee_config_data.organization_id)
        
        try:
            # Create fee configuration - use values from fee_config_dict which has applied defaults
            fee_config = FeeConfiguration(
                organization_type=fee_config_dict['organization_type'],
                organization_id=fee_config_dict['organization_id'],
                subscription_fee_annual=fee_config_dict['subscription_fee_annual'],
                subscription_fee_currency=fee_config_dict['subscription_fee_currency'],
                is_subscription_applicable=bool(fee_config_dict['is_subscription_applicable']),
                subscription_period_months=fee_config_dict['subscription_period_months'],
                listing_fee_percentage=fee_config_dict['listing_fee_percentage'],
                listing_fee_fixed=fee_config_dict['listing_fee_fixed'],
                is_listing_fee_applicable=bool(fee_config_dict['is_listing_fee_applicable']),
                is_listing_fee_payable_on_posting=bool(fee_config_dict['is_listing_fee_payable_on_posting']),
                commitment_fee_percentage=fee_config_dict['commitment_fee_percentage'],
                commitment_fee_fixed=fee_config_dict['commitment_fee_fixed'],
                is_commitment_fee_applicable=bool(fee_config_dict['is_commitment_fee_applicable']),
                success_fee_percentage=fee_config_dict['success_fee_percentage'],
                success_fee_fixed=fee_config_dict['success_fee_fixed'],
                is_success_fee_applicable=bool(fee_config_dict['is_success_fee_applicable']),
                is_success_fee_adjusted_against_listing_fee=bool(fee_config_dict['is_success_fee_adjusted_against_listing_fee']),
                is_subscription_exempt=bool(fee_config_dict['is_subscription_exempt']),
                is_listing_fee_exempt=bool(fee_config_dict['is_listing_fee_exempt']),
                is_success_fee_exempt=bool(fee_config_dict['is_success_fee_exempt']),
                subscription_fee_exemption_reason=fee_config_dict.get('subscription_fee_exemption_reason'),
                listing_fee_exemption_reason=fee_config_dict.get('listing_fee_exemption_reason'),
                success_fee_exemption_reason=fee_config_dict.get('success_fee_exemption_reason'),
                is_active=bool(fee_config_dict['is_active']),
                created_by=created_by or fee_config_dict.get('created_by'),
            )
            
            self.db.add(fee_config)
            self.db.commit()
            self.db.refresh(fee_config)
            
            logger.info(f"Fee configuration created successfully with id: {fee_config.id}")
            return fee_config
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create fee configuration: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create fee configuration: {str(e)}"
            )
    
    def get_fee_configuration_by_id(self, fee_config_id: int) -> FeeConfiguration:
        """Get fee configuration by ID"""
        fee_config = self.db.query(FeeConfiguration).filter(
            FeeConfiguration.id == fee_config_id
        ).first()
        
        if not fee_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fee configuration not found with id: {fee_config_id}"
            )
        
        return fee_config
    
    def get_fee_configuration_by_organization_id(self, organization_id: str) -> FeeConfiguration:
        """Get fee configuration by organization ID"""
        fee_config = self.db.query(FeeConfiguration).filter(
            FeeConfiguration.organization_id == organization_id
        ).first()
        
        if not fee_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fee configuration not found for organization_id: {organization_id}"
            )
        
        return fee_config
    
    def _validate_update_fields_by_organization_type(self, organization_type: str, update_data: dict):
        """Validate that only allowed fields are being updated based on organization type"""
        allowed_fields = {
            'Lender': [
                'subscription_fee_annual',
                'subscription_period_months',
                'updated_by'
            ],
            'Municipality': [
                'listing_fee_percentage',
                'success_fee_percentage',
                'is_listing_fee_exempt',
                'is_success_fee_exempt',
                'is_success_fee_adjusted_against_listing_fee',
                'listing_fee_exemption_reason',
                'success_fee_exemption_reason',
                'updated_by'
            ],
            'Admin': [],
            'Govt': [],
            'NIUA': []
        }
        
        allowed = allowed_fields.get(organization_type, [])
        
        # Check for disallowed fields
        disallowed_fields = []
        for field in update_data.keys():
            if field not in allowed:
                disallowed_fields.append(field)
        
        if disallowed_fields:
            if organization_type in ['Admin', 'Govt', 'NIUA']:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Fee configuration updates are not allowed for {organization_type} organization type"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"The following fields are not allowed for {organization_type} organization type: {', '.join(disallowed_fields)}. "
                           f"Allowed fields: {', '.join([f for f in allowed if f != 'updated_by'])}"
                )
    
    def update_fee_configuration(
        self,
        fee_config_id: int,
        fee_config_data: FeeConfigurationUpdate,
        updated_by: Optional[str] = None
    ) -> FeeConfiguration:
        """Update an existing fee configuration
        
        Admin can modify fee configurations per organization.
        Updates can include:
        - Setting listing fee to 0 for promotional categories or exemptions
        - Modifying subscription fee per organization
        - Updating success fee percentages and netting logic
        """
        logger.info(f"Updating fee configuration with id: {fee_config_id}")
        
        # Get existing fee configuration
        fee_config = self.get_fee_configuration_by_id(fee_config_id)
        
        # Prevent organization_type and organization_id changes
        if fee_config_data.organization_type is not None:
            if fee_config_data.organization_type != fee_config.organization_type:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="organization_type cannot be changed after creation"
                )
        
        if fee_config_data.organization_id is not None:
            if fee_config_data.organization_id != fee_config.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="organization_id cannot be changed after creation"
                )
        
        # Get update data - this will include all fields that were explicitly set in the request
        update_data = fee_config_data.model_dump(exclude_unset=True)
        
        # Remove updated_by from update_data if present, we'll set it separately
        if 'updated_by' in update_data:
            del update_data['updated_by']
        
        # Handle exemption reason fields - convert empty strings to None for consistency
        exemption_reason_fields = [
            'subscription_fee_exemption_reason',
            'listing_fee_exemption_reason',
            'success_fee_exemption_reason'
        ]
        for field in exemption_reason_fields:
            if field in update_data:
                # Convert empty string to None for consistency
                if update_data[field] == "":
                    update_data[field] = None
        
        # Validate fields based on organization type
        self._validate_update_fields_by_organization_type(fee_config.organization_type, update_data)
        
        # Validate percentages if provided
        if fee_config_data.listing_fee_percentage is not None:
            self._validate_percentage(fee_config_data.listing_fee_percentage, "listing_fee_percentage")
        if fee_config_data.success_fee_percentage is not None:
            self._validate_percentage(fee_config_data.success_fee_percentage, "success_fee_percentage")
        
        # Validate organization_id uniqueness if being changed
        if fee_config_data.organization_id is not None and fee_config_data.organization_id != fee_config.organization_id:
            self._validate_organization_id_unique(fee_config_data.organization_id, exclude_id=fee_config_id)
        
        try:
            # Log the update data for debugging
            logger.info(f"Updating fee configuration {fee_config_id} with fields: {list(update_data.keys())}")
            logger.info(f"Exemption reason fields in update_data: subscription={update_data.get('subscription_fee_exemption_reason')}, listing={update_data.get('listing_fee_exemption_reason')}, success={update_data.get('success_fee_exemption_reason')}")
            
            # Update all fields including exemption reasons
            for field, value in update_data.items():
                logger.debug(f"Setting {field} = {value}")
                setattr(fee_config, field, value)
            
            # Set updated_by
            fee_config.updated_by = updated_by or fee_config_data.updated_by
            
            self.db.commit()
            self.db.refresh(fee_config)
            
            logger.info(f"Fee configuration updated successfully with id: {fee_config_id}")
            logger.info(f"Exemption reasons after update - subscription: {fee_config.subscription_fee_exemption_reason}, listing: {fee_config.listing_fee_exemption_reason}, success: {fee_config.success_fee_exemption_reason}")
            return fee_config
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update fee configuration: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update fee configuration: {str(e)}"
            )

