from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationListResponse,
    PerdixOrgDetailResponse,
)
from app.services.organization_service import (
    create_organization_with_local_details,
    create_organization_in_perdix,
    update_organization_in_perdix,
    update_organization_in_perdix_raw,
    update_organization_with_local_details,
    get_organizations_from_perdix,
    get_org_detail_by_org_id,
)

router = APIRouter()


@router.post("/create", status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new organization (branch in Perdix).

    Flow:
    1. Save extra organization details in local DB (perdix_mp_org_details)
    2. Call Perdix branch API to actually create the organization
    3. If Perdix call fails, local DB insert is rolled back.
    """
    try:
        body, status_code, is_json = create_organization_with_local_details(
            payload, db
        )
        return JSONResponse(
            content=body if is_json else {"raw": body},
            status_code=status_code,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create organization: {str(e)}",
        )


@router.put("/organizations/{organization_id}", status_code=status.HTTP_200_OK)
def update_organization(organization_id: int, payload: OrganizationUpdate):
    """Update an existing organization (branch in Perdix)"""
    try:
        body, status_code, is_json = update_organization_in_perdix(organization_id, payload)
        return JSONResponse(content=body if is_json else {"raw": body}, status_code=status_code)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update organization: {str(e)}"
        )


@router.put("/organizations", status_code=status.HTTP_200_OK)
def update_organization_raw(payload: dict, db: Session = Depends(get_db)):
    """
    Update organization (branch) using raw payload from frontend.
    
    Flow (same pattern as create):
    1. Update extra organization details in local DB (perdix_mp_org_details) if org_id exists and fields are provided
    2. Call Perdix branch API to update the organization (with filtered payload - only Perdix fields)
    3. If Perdix call fails, local DB update is rolled back.
    
    Payload can include:
    - Required Perdix fields: id, version, branchCode, bankId, branchName, etc.
    - Optional local fields: panNumber, gstNumber, state, district, lenderType, annualBudgetSize, updatedBy
    
    Local fields (panNumber, gstNumber, state, district, lenderType, etc.) are:
    - Updated in our local database (perdix_mp_org_details)
    - NOT sent to Perdix API (filtered out)
    
    Perdix fields are sent as-is to Perdix API.
    """
    try:
        body, status_code, is_json = update_organization_with_local_details(payload, db)
        return JSONResponse(content=body if is_json else {"raw": body}, status_code=status_code)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update organization: {str(e)}"
        )


@router.get("/organizations", status_code=status.HTTP_200_OK)
def get_organizations():
    """Get all organizations (branches from Perdix)"""
    try:
        body, status_code, is_json = get_organizations_from_perdix()
        return JSONResponse(content=body if is_json else {"raw": body}, status_code=status_code)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch organizations: {str(e)}"
        )


@router.get("/org-details/{org_id}", response_model=PerdixOrgDetailResponse, status_code=status.HTTP_200_OK)
def get_org_detail_by_id(org_id: int, db: Session = Depends(get_db)):
    """
    Get organization details from perdix_mp_org_details table by org_id.
    
    Args:
        org_id: The organization ID to fetch details for
        db: Database session
        
    Returns:
        PerdixOrgDetailResponse: The organization detail record
    """
    try:
        org_detail = get_org_detail_by_org_id(org_id, db)
        return org_detail
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch organization details: {str(e)}"
        )
