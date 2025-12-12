from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.core.database import get_db
from passlib.context import CryptContext
from app.core.config import settings
from app.services.user_service import (
    register_user_with_optional_roles,
    get_users_from_perdix,
    get_user_from_perdix_by_login,
    update_user_in_perdix,
    get_account_from_perdix,
    get_branch_from_perdix,
)
from app.services.user_registration_service import UserRegistrationService
from app.schemas.user_registration import UserRegistrationCreate, UserRegistrationResponse
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/perdix", status_code=status.HTTP_200_OK)
def get_perdix_users(
    branch_name: Optional[str] = Query(None, description="Filter users by branch name"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    per_page: int = Query(10, ge=1, le=100, description="Number of items per page")
):
    """Get users list from Perdix API with pagination and optional branch filter"""
    body, status_code, is_json = get_users_from_perdix(branch_name=branch_name, page=page, per_page=per_page)
    
    if status_code != 200:
        raise HTTPException(
            status_code=status_code,
            detail=body if isinstance(body, str) else body.get("message", "Failed to fetch users from Perdix")
        )
    
    return {
        "status": "success",
        "message": "Users fetched from Perdix successfully",
        "data": body if is_json else {"raw": body}
    }

@router.get("/perdix/{login}", status_code=status.HTTP_200_OK)
def get_perdix_user_by_login(login: str):
    """
    Get single user details from Perdix by login/username.
    
    Additionally fetches branch names from userBranches array:
    - First branch name -> org_type
    - Second branch name -> org_name
    """
    try:
        body, status_code, is_json = get_user_from_perdix_by_login(login)

        if status_code != 200:
            raise HTTPException(
                status_code=status_code,
                detail=body if isinstance(body, str) else body.get("message", "Failed to fetch user from Perdix")
            )

        # If response is not JSON, return as-is
        if not is_json or not isinstance(body, dict):
            return {
                "status": "success",
                "message": "User fetched from Perdix successfully",
                "data": body if is_json else {"raw": body}
            }

        # Extract userBranches array
        user_branches = body.get("userBranches", [])
        
        # Initialize org_type and org_name
        org_type = None
        org_name = None
        
        # Fetch branch names for each branch in userBranches
        if user_branches and len(user_branches) > 0:
            # Fetch first branch name -> org_type
            first_branch_id = user_branches[0].get("branchId")
            if first_branch_id:
                try:
                    branch_body, branch_status, branch_is_json = get_branch_from_perdix(first_branch_id)
                    if branch_status == 200 and branch_is_json and isinstance(branch_body, dict):
                        org_type = branch_body.get("branchName")
                except Exception as exc:
                    # Log error but don't fail the request
                    pass
            
            # Fetch second branch name -> org_name (if exists)
            if len(user_branches) > 1:
                second_branch_id = user_branches[1].get("branchId")
                if second_branch_id:
                    try:
                        branch_body, branch_status, branch_is_json = get_branch_from_perdix(second_branch_id)
                        if branch_status == 200 and branch_is_json and isinstance(branch_body, dict):
                            org_name = branch_body.get("branchName")
                    except Exception as exc:
                        # Log error but don't fail the request
                        pass

        # Add org_type and org_name to the response
        enhanced_body = body.copy()
        enhanced_body["org_type"] = org_type
        enhanced_body["org_name"] = org_name

        return {
            "status": "success",
            "message": "User fetched from Perdix successfully",
            "data": enhanced_body
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user from Perdix: {str(exc)}"
        )

@router.get("/perdix/userid/{userid}", status_code=status.HTTP_200_OK)
def get_perdix_user_by_userid(userid: str):
    """Alias: Get Perdix user by userId (mapped to login)"""
    body, status_code, is_json = get_user_from_perdix_by_login(userid)

    if status_code != 200:
        raise HTTPException(
            status_code=status_code,
            detail=body if isinstance(body, str) else body.get("message", "Failed to fetch user from Perdix")
        )

    return {
        "status": "success",
        "message": "User fetched from Perdix successfully",
        "data": body if is_json else {"raw": body}
    }

@router.put("/perdix", status_code=status.HTTP_200_OK)
def update_perdix_user(payload: dict):
    """Forward user update to Perdix (PUT /api/users)"""
    body, status_code, is_json = update_user_in_perdix(payload)
    return JSONResponse(content=body if is_json else {"raw": body}, status_code=status_code)


@router.get("/account", status_code=status.HTTP_200_OK)
def get_account(
    authorization: str = Header(..., description="Authorization header with JWT token (format: 'JWT <token>' or 'Bearer <token>')")
):
    """
    Get account details from Perdix using JWT token from Authorization header.
    
    The frontend should pass the JWT token in the Authorization header.
    The token can be prefixed with 'JWT ' or 'Bearer ' or sent as-is.
    """
    try:
        # Pass Authorization header as-is to service (service will normalize it)
        body, status_code, is_json = get_account_from_perdix(authorization)
        
        if status_code != 200:
            raise HTTPException(
                status_code=status_code,
                detail=body if isinstance(body, str) else body.get("message", "Failed to fetch account details from Perdix")
            )
        
        return {
            "status": "success",
            "message": "Account details fetched successfully",
            "data": body if is_json else {"raw": body}
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch account details: {str(exc)}"
        )


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register_user(
    registration_data: UserRegistrationCreate,
    db: Session = Depends(get_db),
    created_by: Optional[str] = Header(None, alias="X-Created-By")
):
    """
    Register a new user:
    1. Accepts flexible payload based on organization type
    2. Extracts common fields required for Perdix API
    3. Calls Perdix API to create user
    4. Stores user details in local database
    
    The payload can vary based on organization type, but must include:
    - Common fields: organization_name, organization_type, user_name, user_email, 
      user_mobile_number, password, confirm_password, user_role
    - Perdix-specific fields: login, valid_until, branch_id, branch_name, user_branches
    """
    service = UserRegistrationService(db)
    user = service.register_user(registration_data, created_by=created_by)
    
    return {
        "status": "success",
        "message": "User registered successfully",
        "data": user.model_dump()
    }


@router.get("/register/{user_id}", response_model=dict, status_code=status.HTTP_200_OK)
def get_registered_user(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get registered user details by user_id"""
    service = UserRegistrationService(db)
    user = service.get_user_by_id(user_id)
    
    return {
        "status": "success",
        "message": "User fetched successfully",
        "data": user.model_dump()
    }
