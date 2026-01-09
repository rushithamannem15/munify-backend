from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class FeeConfigurationCreate(BaseModel):
    """Schema for creating a fee configuration
    
    Fee Structure:
    - Subscription Fee: Primarily for Lenders (annual, renewal-based). May not be charged in first phase.
    - Listing Fee: Applied to Municipalities for project listing, as % of project fund requirement. Can be set to 0.
    - Success Fee: For Municipalities, charged upon successful closure/funding (typically 0.5-1% of funded amount).
    
    Exemptions:
    - Admins: Fully exempt from subscription (set is_subscription_exempt=True)
    - Govt/NIUA: Exempt from subscription and listing fees (set is_subscription_exempt=True and is_listing_fee_exempt=True)
    """
    organization_type: str = Field(..., description="Type of organization: Lender, Municipality, Admin, Govt, NIUA")
    organization_id: str = Field(..., description="Unique organization identifier")
    
    # Subscription Fee (Primarily for Lenders)
    subscription_fee_annual: Optional[Decimal] = Field(None, description="Annual subscription fee amount")
    subscription_fee_currency: Optional[str] = Field(None, description="Currency for subscription fee (default: INR)")
    is_subscription_applicable: bool = Field(False, description="Whether subscription fee is applicable (typically True for Lenders)")
    subscription_period_months: Optional[int] = Field(None, description="Subscription period in months (default: 12 for annual)")
    
    # Listing Fee (For Municipalities - % of project fund requirement)
    listing_fee_percentage: Optional[Decimal] = Field(None, description="Listing fee as percentage of project fund requirement (0-100). Can be set to 0 for exemptions")
    listing_fee_fixed: Optional[Decimal] = Field(None, description="Fixed listing fee amount (alternative to percentage)")
    is_listing_fee_applicable: bool = Field(False, description="Whether listing fee is applicable (typically True for Municipalities)")
    is_listing_fee_payable_on_posting: bool = Field(False, description="Whether listing fee is payable on project posting (not dependent on success). Typically True for Municipalities")
    
    # Commitment Fee (Future use - not in current requirements)
    commitment_fee_percentage: Optional[Decimal] = Field(None, description="Commitment fee as percentage (future use)")
    commitment_fee_fixed: Optional[Decimal] = Field(None, description="Fixed commitment fee amount (future use)")
    is_commitment_fee_applicable: bool = Field(False, description="Whether commitment fee is applicable (future use)")
    
    # Success Fee (For Municipalities - on project closure/sanction)
    success_fee_percentage: Optional[Decimal] = Field(None, description="Success fee as percentage of funded amount (0-100, typically 0.5-1%)")
    success_fee_fixed: Optional[Decimal] = Field(None, description="Fixed success fee amount (alternative to percentage)")
    is_success_fee_applicable: bool = Field(False, description="Whether success fee is applicable (typically True for Municipalities)")
    is_success_fee_adjusted_against_listing_fee: bool = Field(False, description="Whether success fee is adjusted against listing fee already paid (netting logic: Success Fee - Listing Fee)")
    
    # Exemptions
    is_subscription_exempt: bool = Field(False, description="Whether subscription fee is exempt (True for Admins and Govt/NIUA)")
    is_listing_fee_exempt: bool = Field(False, description="Whether listing fee is exempt (True for Govt/NIUA invited users)")
    is_success_fee_exempt: bool = Field(False, description="Whether success fee is exempt (for specific exemptions)")
    subscription_fee_exemption_reason: Optional[str] = Field(None, description="Reason for subscription fee exemption (e.g., 'Admin user', 'Govt/NIUA invited')")
    listing_fee_exemption_reason: Optional[str] = Field(None, description="Reason for listing fee exemption (e.g., 'Govt/NIUA invited', 'Promotional category')")
    success_fee_exemption_reason: Optional[str] = Field(None, description="Reason for success fee exemption (e.g., 'Promotional category', 'Sponsored project')")
    
    # Status
    is_active: bool = Field(False, description="Whether the configuration is active")
    created_by: Optional[str] = Field(None, description="User who created the configuration (Munify Admin)")
    
    @field_validator('organization_type')
    @classmethod
    def validate_organization_type(cls, v):
        allowed_types = ['Lender', 'Municipality', 'Admin', 'Govt', 'NIUA']
        if v not in allowed_types:
            raise ValueError(f"organization_type must be one of: {', '.join(allowed_types)}")
        return v
    
    @field_validator('listing_fee_percentage', 'success_fee_percentage')
    @classmethod
    def validate_percentage(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Percentage must be between 0 and 100")
        return v
    
    model_config = ConfigDict(from_attributes=True)


class FeeConfigurationUpdate(BaseModel):
    """Schema for updating a fee configuration"""
    organization_type: Optional[str] = Field(None, description="Type of organization")
    organization_id: Optional[str] = Field(None, description="Organization identifier")
    
    # Subscription Fee
    subscription_fee_annual: Optional[Decimal] = None
    subscription_fee_currency: Optional[str] = None
    is_subscription_applicable: Optional[bool] = None
    subscription_period_months: Optional[int] = None
    
    # Listing Fee
    listing_fee_percentage: Optional[Decimal] = None
    listing_fee_fixed: Optional[Decimal] = None
    is_listing_fee_applicable: Optional[bool] = None
    is_listing_fee_payable_on_posting: Optional[bool] = None
    
    # Commitment Fee
    commitment_fee_percentage: Optional[Decimal] = None
    commitment_fee_fixed: Optional[Decimal] = None
    is_commitment_fee_applicable: Optional[bool] = None
    
    # Success Fee
    success_fee_percentage: Optional[Decimal] = None
    success_fee_fixed: Optional[Decimal] = None
    is_success_fee_applicable: Optional[bool] = None
    is_success_fee_adjusted_against_listing_fee: Optional[bool] = None
    
    # Exemptions
    is_subscription_exempt: Optional[bool] = None
    is_listing_fee_exempt: Optional[bool] = None
    is_success_fee_exempt: Optional[bool] = None
    subscription_fee_exemption_reason: Optional[str] = None
    listing_fee_exemption_reason: Optional[str] = None
    success_fee_exemption_reason: Optional[str] = None
    
    # Status
    is_active: Optional[bool] = None
    updated_by: Optional[str] = Field(None, description="User who updated the configuration")
    
    @field_validator('organization_type')
    @classmethod
    def validate_organization_type(cls, v):
        if v is not None:
            allowed_types = ['Lender', 'Municipality', 'Admin', 'Govt', 'NIUA']
            if v not in allowed_types:
                raise ValueError(f"organization_type must be one of: {', '.join(allowed_types)}")
        return v
    
    @field_validator('listing_fee_percentage', 'success_fee_percentage')
    @classmethod
    def validate_percentage(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Percentage must be between 0 and 100")
        return v
    
    model_config = ConfigDict(from_attributes=True)


class FeeConfigurationResponse(BaseModel):
    """Schema for fee configuration response"""
    id: int
    organization_type: str
    organization_id: str
    
    # Subscription Fee
    subscription_fee_annual: Optional[Decimal] = None
    subscription_fee_currency: Optional[str] = None
    is_subscription_applicable: bool = False
    subscription_period_months: Optional[int] = None
    
    # Listing Fee
    listing_fee_percentage: Optional[Decimal] = None
    listing_fee_fixed: Optional[Decimal] = None
    is_listing_fee_applicable: Optional[bool] = None
    is_listing_fee_payable_on_posting: Optional[bool] = None
    
    # Commitment Fee
    commitment_fee_percentage: Optional[Decimal] = None
    commitment_fee_fixed: Optional[Decimal] = None
    is_commitment_fee_applicable: Optional[bool] = None
    
    # Success Fee
    success_fee_percentage: Optional[Decimal] = None
    success_fee_fixed: Optional[Decimal] = None
    is_success_fee_applicable: Optional[bool] = None
    is_success_fee_adjusted_against_listing_fee: Optional[bool] = None
    
    # Exemptions
    is_subscription_exempt: Optional[bool] = None
    is_listing_fee_exempt: Optional[bool] = None
    is_success_fee_exempt: Optional[bool] = None
    subscription_fee_exemption_reason: Optional[str] = None
    listing_fee_exemption_reason: Optional[str] = None
    success_fee_exemption_reason: Optional[str] = None
    
    # Status & Audit
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

