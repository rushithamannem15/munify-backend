from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Dict, Any
from app.models.perdix_user_detail import PerdixUserDetail
from app.schemas.user_registration import UserRegistrationCreate, PerdixUserCreatePayload, UserRegistrationResponse
from app.services.user_service import create_user_in_perdix
from app.core.logging import get_logger

logger = get_logger("services.user_registration")


class UserRegistrationService:
    def __init__(self, db: Session):
        self.db = db
    
    def _build_perdix_payload(self, registration_data: UserRegistrationCreate) -> Dict[str, Any]:
        """Build Perdix API payload from frontend registration data"""
        # Extract organization info
        org_id = registration_data.organization.id
        org_name = registration_data.organization.orgName
        
        # Build userBranches array - use organization as branch
        user_branches = [
            {
                "branchId": org_id,
                "titleExpr": org_name
            }
        ]
        
        # Convert userRoles from Pydantic models to dict format for Perdix API
        user_roles = []
        if registration_data.userRoles:
            for role in registration_data.userRoles:
                user_roles.append({
                    "userId": role.userId,
                    "userName": role.userName,
                    "roleId": role.roleId,
                    "roleName": role.roleName,
                    "userRoleId": role.userRoleId,
                    "id": role.id
                })
        
        # Build Perdix payload with hardcoded values and extracted data
        perdix_payload = {
            "roleCode": "A",  # Hardcoded
            "activated": True,  # Hardcoded
            "userState": "ACTIVE",  # Hardcoded
            "userType": "A",  # Hardcoded
            "bankName": "Witfin",  # Use organization name
            "validUntil": "2035-12-31",  # Hardcoded future date
            "accessType": "BRANCH",  # Hardcoded
            "imeiNumber": "",  # Hardcoded empty
            "langKey": "en",  # Hardcoded
            "userRoles": user_roles,  # From frontend payload
            "userBranches": user_branches,
            "userName": registration_data.fullName,
            "login": registration_data.login,
            "password": registration_data.password,
            "confirmPassword": registration_data.confirmPassword,
            "email": registration_data.email,
            "mobileNumber": registration_data.mobileNumber,  # Already int from frontend
            "branchId": registration_data.orgtypeObj.id,  # Use organization ID
            "branchName": registration_data.orgtypeObj.orgTypeName,  # Use organization name
            "changePasswordOnLogin": True,  # Hardcoded
        }
        
        return perdix_payload
    
    def register_user(self, registration_data: UserRegistrationCreate, created_by: str = None) -> UserRegistrationResponse:
        """
        Register a new user:
        1. Build Perdix payload from registration data
        2. Call Perdix API to create user
        3. Extract user_id from Perdix response
        4. Store user details in local database
        """
        logger.info(f"Starting user registration for email: {registration_data.email}, login: {registration_data.login}")
        
        try:
            # Build Perdix payload
            perdix_payload = self._build_perdix_payload(registration_data)
            logger.debug(f"Perdix payload prepared: {perdix_payload.get('login')}")
            
            # Call Perdix API
            perdix_response, perdix_status_code, is_json = create_user_in_perdix(perdix_payload)
            
            # Check if Perdix API call was successful
            if perdix_status_code not in (200, 201):
                # Log the full response for debugging
                logger.error(f"Perdix API returned status {perdix_status_code}. Response: {perdix_response}")
                
                # Return Perdix error response directly to frontend (as-is)
                raise HTTPException(
                    status_code=perdix_status_code,
                    detail=perdix_response
                )
            
            if not is_json or not isinstance(perdix_response, dict):
                logger.error(f"Invalid Perdix response format: {perdix_response}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Invalid response format from Perdix API"
                )
            
            # Get user_id from Perdix response (login field)
            perdix_user_id = perdix_response.get("login")
            logger.info(f"User created in Perdix with user_id: {perdix_user_id}")
            
            # Extract user role ID (from userRoles array if available)
            user_role_id = registration_data.get_user_role_id() or 0  # Default to 0 if not provided
            
            # Get payload as dict to access all fields (including any extra fields)
            payload_dict = registration_data.model_dump()
            
            # Store user details in local database
            # Get values from payload if available, otherwise None
            db_user = PerdixUserDetail(
                organization_name=registration_data.get_organization_name(),
                organization_type=registration_data.get_organization_type(),
                user_id=perdix_user_id,
                user_role=user_role_id,
                user_name=registration_data.fullName,
                user_email=registration_data.email,
                user_mobile_number=str(registration_data.mobileNumber),
                designation=payload_dict.get('designation'),
                registration_number=payload_dict.get('regulatoryRegistrationNo'),
                is_tc_accepted=payload_dict.get('is_tc_accepted', False),
                state=payload_dict.get('state'),
                district=payload_dict.get('district'),
                gstn_ulb_code=payload_dict.get('gstn_ulb_code'),
                annual_budget_size=payload_dict.get('annual_budget_size'),
                status=payload_dict.get('status', 'ACTIVE'),
                is_mobile_verified=payload_dict.get('is_mobile_verified', False),
                mobile_verified_at=payload_dict.get('mobile_verified_at'),
                created_by=created_by,
                updated_by=created_by,
                file_id=payload_dict.get('file_id'),
            )
            
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            
            logger.info(f"User registered successfully: {db_user.id}, user_id: {db_user.user_id}")
            
            return UserRegistrationResponse.model_validate(db_user)
            
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error during user registration: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to register user: {str(e)}"
            )
    
    def get_user_by_id(self, user_id: str) -> UserRegistrationResponse:
        """Get user details by user_id"""
        user = self.db.query(PerdixUserDetail).filter(PerdixUserDetail.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with user_id {user_id} not found"
            )
        return UserRegistrationResponse.model_validate(user)

