import httpx
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.perdix_org_detail import PerdixOrgDetail
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


def create_organization_in_perdix(payload: OrganizationCreate) -> tuple:
    """Create a new organization (branch) in Perdix system"""
    base_url = settings.PERDIX_BASE_URL.rstrip("/")
    url = f"{base_url}/api/branch"
    
    if not settings.PERDIX_JWT:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Perdix JWT is not configured")
    
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"JWT {settings.PERDIX_JWT}",
        "origin": settings.PERDIX_ORIGIN,
        "page_uri": "Page/Engine/management.BranchMaintenance",
        "referer": f"{settings.PERDIX_ORIGIN}/perdix-client/",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    
    organization_payload = {
        "bankId": payload.bank_id,
        "parentBranchId": payload.parent_branch_id,
        "branchName": payload.branch_name,
        "branchMailId": str(payload.branch_mail_id),
        "pinCode": payload.pin_code,
        "branchOpenDate": payload.branch_open_date,
        "cashLimit": payload.cash_limit,
        "fingerPrintDeviceType": payload.finger_print_device_type
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=organization_payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    try:
        return response.json(), response.status_code, True
    except ValueError:
        return response.text, response.status_code, False


def update_organization_in_perdix(organization_id: int, payload: OrganizationUpdate) -> tuple:
    """Update an existing organization (branch) in Perdix system"""
    base_url = settings.PERDIX_BASE_URL.rstrip("/")
    url = f"{base_url}/api/branch"
    
    if not settings.PERDIX_JWT:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Perdix JWT is not configured")
    
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"JWT {settings.PERDIX_JWT}",
        "origin": settings.PERDIX_ORIGIN,
        "page_uri": "Page/Engine/management.BranchMaintenance",
        "referer": f"{settings.PERDIX_ORIGIN}/perdix-client/",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    
    # Build update payload with only provided fields
    organization_payload = {"id": organization_id}
    if payload.bank_id is not None:
        organization_payload["bankId"] = payload.bank_id
    if payload.parent_branch_id is not None:
        organization_payload["parentBranchId"] = payload.parent_branch_id
    if payload.branch_name is not None:
        organization_payload["branchName"] = payload.branch_name
    if payload.branch_mail_id is not None:
        organization_payload["branchMailId"] = str(payload.branch_mail_id)
    if payload.pin_code is not None:
        organization_payload["pinCode"] = payload.pin_code
    if payload.branch_open_date is not None:
        organization_payload["branchOpenDate"] = payload.branch_open_date
    if payload.cash_limit is not None:
        organization_payload["cashLimit"] = payload.cash_limit
    if payload.finger_print_device_type is not None:
        organization_payload["fingerPrintDeviceType"] = payload.finger_print_device_type
    # Add fields that are computed/server-side and not from frontend
    # Always include branchCode = id as per Perdix behavior in sample payloads
    organization_payload["branchCode"] = organization_id
    # Set version default to 0 if not provided from frontend
    organization_payload["version"] = 2
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.put(url, headers=headers, json=organization_payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    
    try:
        return response.json(), response.status_code, True
    except ValueError:
        return response.text, response.status_code, False


def _validate_extra_fields(payload: OrganizationCreate) -> None:
    """
    Validate extra fields coming from frontend based on orgType.

    - If orgType is "Lender":
      - Requires: typeOfLender, panNumber, gstNumber
    - If orgType is "Muncipalties" (as per requirement text):
      - Requires: state, district, panNumber, gstNumber
    """
    org_type = (payload.org_type or "").strip()

    if not org_type:
        # Extra validation is only enforced when orgType is provided.
        return

    missing_fields = []

    if org_type == "Lender":
        if not payload.type_of_lender:
            missing_fields.append("typeOfLender")
        if not payload.pan_number:
            missing_fields.append("panNumber")
        if not payload.gst_number:
            missing_fields.append("gstNumber")
    elif org_type == "Muncipalties":
        if not payload.state:
            missing_fields.append("state")
        if not payload.district:
            missing_fields.append("district")
        if not payload.pan_number:
            missing_fields.append("panNumber")
        if not payload.gst_number:
            missing_fields.append("gstNumber")

    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required fields for orgType '{org_type}': {', '.join(missing_fields)}",
        )


def create_organization_with_local_details(
    payload: OrganizationCreate,
    db,
) -> tuple:
    """
    Create organization in two steps within a single transactional flow:
    1. Save extra details in our DB table `perdix_mp_org_details`
    2. Call Perdix branch API to create the organization

    If the Perdix call fails, the local DB insert is rolled back.
    """
    # Business validation based on org type
    _validate_extra_fields(payload)

    org_detail = PerdixOrgDetail(
        pan_number=payload.pan_number,
        gst_number=payload.gst_number,
        state=payload.state,
        district=payload.district,
        type_of_lender=payload.type_of_lender,
        annual_budget_size=payload.annual_budget_size,
        created_by=payload.created_by,
        updated_by=payload.updated_by,
    )

    try:
        # Stage 1: save local details but do not commit yet
        db.add(org_detail)
        db.flush()

        # Stage 2: call Perdix
        body, status_code, is_json = create_organization_in_perdix(payload)

        # If Perdix returns an error status, rollback our transaction
        if status_code >= 400:
            db.rollback()
            # Surface Perdix error to client
            raise HTTPException(
                status_code=status_code,
                detail=body if is_json else str(body),
            )

        # If Perdix response contains an organization/branch identifier,
        # map it to our local record.
        if is_json and isinstance(body, dict):
            # Adjust keys as per actual Perdix response structure
            perdix_org_id = (
                body.get("id")
            )
            if perdix_org_id is not None:
                org_detail.org_id = perdix_org_id
                db.flush()

        # All good – commit our local transaction
        db.commit()

        return body, status_code, is_json
    except HTTPException:
        # Already rolled back above for HTTP errors coming from Perdix
        raise
    except Exception:
        # Any other unexpected error – rollback and re-raise
        db.rollback()
        raise


def update_organization_in_perdix_raw(payload: dict) -> tuple:
    """Update organization (branch) in Perdix using the exact frontend payload (no server-side mutation)."""
    base_url = settings.PERDIX_BASE_URL.rstrip("/")
    url = f"{base_url}/api/branch"

    if not settings.PERDIX_JWT:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Perdix JWT is not configured")

    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"JWT {settings.PERDIX_JWT}",
        "origin": settings.PERDIX_ORIGIN,
        "page_uri": "Page/Engine/management.BranchMaintenance",
        "referer": f"{settings.PERDIX_ORIGIN}/perdix-client/",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.put(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    try:
        return response.json(), response.status_code, True
    except ValueError:
        return response.text, response.status_code, False


def update_organization_with_local_details(payload: dict, db) -> tuple:
    """
    Update organization in two steps within a single transactional flow:
    1. Update extra details in our DB table `perdix_mp_org_details` (if org_id exists and fields are provided)
    2. Call Perdix branch API to update the organization
    
    If the Perdix call fails, the local DB update is rolled back.
    
    This function follows the same pattern as create_organization_with_local_details:
    - Updates local DB first
    - Then calls Perdix API
    - Rolls back on Perdix failure
    
    Args:
        payload: Raw dict payload from frontend (must include 'id' for org_id)
        db: Database session
        
    Returns:
        tuple: (response_body, status_code, is_json)
        
    Raises:
        HTTPException: If org_id not found in payload or Perdix update fails
    """
    # Extract org_id from payload (frontend sends 'id' as the organization ID)
    org_id = payload.get("id")
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field 'id' in payload"
        )
    
    # Try to find existing org_detail record by org_id
    org_detail = db.query(PerdixOrgDetail).filter(PerdixOrgDetail.org_id == org_id).first()
    
    # Fields that we store locally (these should NOT be sent to Perdix)
    # Map from frontend field names to model attribute names
    local_field_mapping = {
        "panNumber": "pan_number",
        "gstNumber": "gst_number",
        "state": "state",
        "district": "district",
        "lenderType": "type_of_lender",  # Frontend sends lenderType, we store as type_of_lender
        "annualBudgetSize": "annual_budget_size",
        "updatedBy": "updated_by",
    }
    
    # Fields that Perdix API accepts (ONLY these should be sent to Perdix)
    # Based on the demo payload provided by user
    perdix_fields = {
        "bankId",
        "id",
        "version",
        "branchName",
        "branchCode",
        "parentBranchId",
        "branchOpenDate",
        "branchMailId",
        "cashLimit",
        "pinCode",
        "fingerPrintDeviceType"
    }
    
    # Track if we need to update local DB
    local_update_needed = False
    
    try:
        # Stage 1: Update local DB if record exists and fields are provided
        if org_detail:
            for frontend_field, model_attr in local_field_mapping.items():
                if frontend_field in payload:
                    value = payload[frontend_field]
                    # Update the field (allows None/empty string to clear fields)
                    setattr(org_detail, model_attr, value)
                    local_update_needed = True
            
            if local_update_needed:
                db.flush()  # Flush but don't commit yet
        
        # Stage 2: Create filtered payload for Perdix (ONLY Perdix-specific fields)
        # Remove all local-only fields before sending to Perdix
        perdix_payload = {
            key: value 
            for key, value in payload.items() 
            if key in perdix_fields
        }
        
        # Ensure required fields are present
        if "id" not in perdix_payload:
            perdix_payload["id"] = org_id
        
        # Call Perdix update with filtered payload (only Perdix fields)
        body, status_code, is_json = update_organization_in_perdix_raw(perdix_payload)
        
        # If Perdix returns an error status, rollback our transaction
        if status_code >= 400:
            if local_update_needed:
                db.rollback()
            # Surface Perdix error to client
            raise HTTPException(
                status_code=status_code,
                detail=body if is_json else str(body),
            )
        
        # All good – commit our local transaction
        if local_update_needed:
            db.commit()
        
        return body, status_code, is_json
        
    except HTTPException:
        # Already rolled back above for HTTP errors coming from Perdix
        raise
    except Exception as e:
        # Any other unexpected error – rollback and re-raise
        if local_update_needed:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update organization: {str(e)}"
        )


def get_organizations_from_perdix() -> tuple:
    """Get all organizations (branches) from Perdix system"""
    base_url = settings.PERDIX_BASE_URL.rstrip("/")
    url = f"{base_url}/api/branch"
    
    if not settings.PERDIX_JWT:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Perdix JWT is not configured")
    
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"JWT {settings.PERDIX_JWT}",
        "origin": settings.PERDIX_ORIGIN,
        "referer": f"{settings.PERDIX_ORIGIN}/perdix-client/",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    
    try:
        return response.json(), response.status_code, True
    except ValueError:
        return response.text, response.status_code, False


def get_org_detail_by_org_id(org_id: int, db) -> PerdixOrgDetail:
    """
    Get organization details from perdix_mp_org_details table by org_id.
    
    Args:
        org_id: The organization ID to search for
        db: Database session
        
    Returns:
        PerdixOrgDetail: The organization detail record
        
    Raises:
        HTTPException: If organization detail not found
    """
    org_detail = db.query(PerdixOrgDetail).filter(PerdixOrgDetail.org_id == org_id).first()
    
    if not org_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization detail not found for org_id: {org_id}"
        )
    
    return org_detail