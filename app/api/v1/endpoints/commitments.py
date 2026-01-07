from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Header
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.commitment import (
    CommitmentCreate,
    CommitmentUpdate,
    CommitmentResponse,
    CommitmentListResponse,
    CommitmentApproveRequest,
    CommitmentRejectRequest,
    CommitmentStatusChangeRequest,
    CommitmentHistoryResponse,
)
from app.schemas.project import ProjectCommitmentsSummaryListResponse
from app.services.commitment_service import CommitmentService
from app.services.project_service import ProjectService
from app.services.commitment_document_service import CommitmentDocumentService
from app.schemas.file import FileResponse
from app.core.logging import get_logger
from decimal import Decimal

logger = get_logger("api.commitments")


router = APIRouter()


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_commitment(
    commitment_data: CommitmentCreate,
    db: Session = Depends(get_db),
):
    """Create a new commitment for a project (initial status: under_review)."""
    try:
        service = CommitmentService(db)
        commitment = service.create_commitment(commitment_data)
        commitment_response = CommitmentResponse.model_validate(commitment)
        return {
            "status": "success",
            "message": "Commitment created successfully",
            "data": commitment_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create commitment: {str(exc)}",
        )


@router.post("/with-documents", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_commitment_with_documents(
    # Commitment fields as Form data
    project_reference_id: str = Form(..., description="Project reference ID for which the commitment is made"),
    organization_type: str = Form(..., description="Type of lender organization"),
    organization_id: str = Form(..., description="Lender organization ID"),
    committed_by: str = Form(..., description="User or entity who committed the funds"),
    amount: str = Form(..., description="Committed amount"),
    currency: str = Form("INR", description="Currency code (default: INR)"),
    funding_mode: str = Form(..., description="Funding mode: loan, grant, csr"),
    interest_rate: Optional[str] = Form(None, description="Interest rate (for loans)"),
    tenure_months: Optional[int] = Form(None, description="Tenure in months (for loans)"),
    terms_conditions_text: Optional[str] = Form(None, description="Free-text terms & conditions from lender"),
    created_by: Optional[str] = Form(None, description="User who created the commitment"),
    # Document file (required) - single file only
    # Note: Frontend sends field name "files" but we receive it as single file
    files: UploadFile = File(..., description="File to upload (field name from frontend: 'files')"),
    document_types: str = Form(..., description="Document type (sanction_letter, approval_note, kyc, terms_sheet, due_diligence) - field name from frontend: 'document_types'"),
    access_level: str = Form("private", description="Access level for uploaded files: public, restricted, or private"),
    is_required: bool = Form(True, description="Whether uploaded documents are required"),
    db: Session = Depends(get_db),
    uploaded_by: Optional[str] = Header(None, alias="user_id", description="User ID who uploaded the file")
):
    """
    Create a new commitment for a project with optional document upload.
    
    This endpoint:
    1. Creates the commitment record first
    2. Then uploads the provided file as a commitment document (if provided)
    3. Returns the commitment with uploaded document details
    
    **Document Types:**
    - sanction_letter: Sanction Letter
    - approval_note: Approval Note
    - kyc: KYC Documents
    - terms_sheet: Terms Sheet
    - due_diligence: Due Diligence Documents
    
    **Note**: Both file and document_types are required fields.
    """
    try:
       
        
        if not uploaded_by:
            uploaded_by = committed_by or created_by
        
        if not uploaded_by:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID is required. Please provide user_id header or committed_by."
            )
        
        # Parse commitment data
        try:
            amount_decimal = Decimal(amount)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid amount format"
            )
        
        interest_rate_decimal = None
        if interest_rate:
            try:
                interest_rate_decimal = Decimal(interest_rate)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid interest_rate format"
                )
        
        # Create CommitmentCreate schema
        commitment_create = CommitmentCreate(
            project_reference_id=project_reference_id,
            organization_type=organization_type,
            organization_id=organization_id,
            committed_by=committed_by,
            amount=amount_decimal,
            currency=currency,
            funding_mode=funding_mode,
            interest_rate=interest_rate_decimal,
            tenure_months=tenure_months,
            terms_conditions_text=terms_conditions_text,
            created_by=created_by or uploaded_by
        )
        
        # Step 1: Create commitment
        commitment_service = CommitmentService(db)
        commitment = commitment_service.create_commitment(commitment_create)
        commitment_id = commitment.id
        
        # Step 2: Upload document (file is mandatory)
        uploaded_document = None
        # Upload the file
        document_service = CommitmentDocumentService(db)
        try:
            commitment_doc = document_service.upload_commitment_file(
                file=files,  # Frontend sends as "files" but it's a single file
                commitment_id=commitment_id,
                document_type=document_types,  # Frontend sends as "document_types" but it's a single value
                uploaded_by=uploaded_by,
                organization_id=organization_id,
                access_level=access_level,
                is_required=is_required,
                created_by=created_by or uploaded_by
            )
            uploaded_document = {
                "file_id": commitment_doc.file_id,
                "commitment_document_id": commitment_doc.id,
                "document_type": commitment_doc.document_type
            }
        except HTTPException as e:
            # Note: Commitment is already created and committed.
            # If file upload fails, commitment still exists (user can retry file upload).
            # We don't rollback commitment creation as it's already committed.
            # Log warning but don't fail the request - return commitment with warning
            logger.warning(f"Commitment {commitment_id} created but document upload failed: {e.detail}")
            # Continue to return commitment (file upload can be retried later)
        except Exception as e:
            # Note: Commitment is already created and committed.
            logger.error(f"Commitment {commitment_id} created but document upload error: {str(e)}", exc_info=True)
            # Continue to return commitment (file upload can be retried later)
        
        # Get commitment with documents if file was uploaded successfully
        if uploaded_document:
            commitment_data = commitment_service.get_commitment_with_documents(commitment_id)
            message = "Commitment created successfully with document"
        else:
            # File upload failed but commitment was created
            commitment_response = CommitmentResponse.model_validate(commitment)
            commitment_data = commitment_response.model_dump()
            message = "Commitment created successfully, but document upload failed. You can upload the document later using POST /api/v1/commitments/{}/files/upload".format(commitment_id)
        
        return {
            "status": "success",
            "message": message,
            "data": commitment_data,
            "uploaded_document": uploaded_document
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error creating commitment with documents: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create commitment: {str(exc)}",
        )


@router.get(
    "/{commitment_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def get_commitment(
    commitment_id: int,
    include_documents: bool = Query(False, description="Include documents with file details in response"),
    db: Session = Depends(get_db),
):
    """
    Get a single commitment by ID.
    
    If `include_documents=true`, the response will include all documents
    with their file details from perdix_mp_files table.
    """
    try:
        service = CommitmentService(db)
        
        if include_documents:
            commitment_data = service.get_commitment_with_documents(commitment_id)
            return {
                "status": "success",
                "message": "Commitment fetched successfully",
                "data": commitment_data,
            }
        else:
            commitment = service.get_commitment_by_id(commitment_id)
            commitment_response = CommitmentResponse.model_validate(commitment)
            return {
                "status": "success",
                "message": "Commitment fetched successfully",
                "data": commitment_response,
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch commitment: {str(exc)}",
        )


@router.get(
    "/",
    response_model=CommitmentListResponse,
    status_code=status.HTTP_200_OK,
)
def list_commitments(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    project_reference_id: str | None = Query(
        None, description="Filter by project reference ID"
    ),
    organization_id: str | None = Query(
        None, description="Filter by lender organization ID"
    ),
    organization_type: str | None = Query(
        None, description="Filter by lender organization type"
    ),
    status_filter: str | None = Query(
        None,
        description="Filter by commitment status (under_review, approved, rejected, withdrawn, funded, completed)",
    ),
    db: Session = Depends(get_db),
):
    """List commitments with optional filters and pagination."""
    try:
        service = CommitmentService(db)
        commitments, total = service.list_commitments(
            skip=skip,
            limit=limit,
            project_reference_id=project_reference_id,
            organization_id=organization_id,
            organization_type=organization_type,
            status_filter=status_filter,
        )
        data = [CommitmentResponse.model_validate(c) for c in commitments]
        return {
            "status": "success",
            "message": "Commitments fetched successfully",
            "data": data,
            "total": total,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch commitments: {str(exc)}",
        )


@router.put(
    "/{commitment_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def update_commitment(
    commitment_id: int,
    commitment_data: CommitmentUpdate,
    db: Session = Depends(get_db),
):
    """Update commitment details (allowed only in under_review status)."""
    try:
        service = CommitmentService(db)
        commitment = service.update_commitment(commitment_id, commitment_data)
        commitment_response = CommitmentResponse.model_validate(commitment)
        return {
            "status": "success",
            "message": "Commitment updated successfully",
            "data": commitment_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update commitment: {str(exc)}",
        )


@router.post(
    "/{commitment_id}/withdraw",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def withdraw_commitment(
    commitment_id: int,
    payload: CommitmentStatusChangeRequest,
    db: Session = Depends(get_db),
):
    """Withdraw a commitment (allowed only in under_review status)."""
    try:
        service = CommitmentService(db)
        commitment = service.withdraw_commitment(commitment_id, payload.updated_by)
        commitment_response = CommitmentResponse.model_validate(commitment)
        return {
            "status": "success",
            "message": "Commitment withdrawn successfully",
            "data": commitment_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to withdraw commitment: {str(exc)}",
        )


@router.post(
    "/{commitment_id}/approve",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def approve_commitment(
    commitment_id: int,
    payload: CommitmentApproveRequest,
    db: Session = Depends(get_db),
):
    """Approve a commitment (under_review -> approved)."""
    try:
        service = CommitmentService(db)
        commitment = service.approve_commitment(
            commitment_id=commitment_id,
            approved_by=payload.approved_by,
            approval_notes=payload.approval_notes,
        )
        commitment_response = CommitmentResponse.model_validate(commitment)
        return {
            "status": "success",
            "message": "Commitment approved successfully",
            "data": commitment_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve commitment: {str(exc)}",
        )


@router.post(
    "/{commitment_id}/reject",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def reject_commitment(
    commitment_id: int,
    payload: CommitmentRejectRequest,
    db: Session = Depends(get_db),
):
    """Reject a commitment (under_review -> rejected)."""
    try:
        service = CommitmentService(db)
        commitment = service.reject_commitment(
            commitment_id=commitment_id,
            approved_by=payload.approved_by,
            rejection_reason=payload.rejection_reason,
            rejection_notes=payload.rejection_notes,
        )
        commitment_response = CommitmentResponse.model_validate(commitment)
        return {
            "status": "success",
            "message": "Commitment rejected successfully",
            "data": commitment_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject commitment: {str(exc)}",
        )


@router.post(
    "/{commitment_id}/fund",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def fund_commitment(
    commitment_id: int,
    payload: CommitmentStatusChangeRequest,
    db: Session = Depends(get_db),
):
    """Mark a commitment as funded (approved -> funded)."""
    try:
        service = CommitmentService(db)
        commitment = service.mark_funded(commitment_id, payload.updated_by)
        commitment_response = CommitmentResponse.model_validate(commitment)
        return {
            "status": "success",
            "message": "Commitment marked as funded successfully",
            "data": commitment_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark commitment as funded: {str(exc)}",
        )


@router.post(
    "/{commitment_id}/complete",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def complete_commitment(
    commitment_id: int,
    payload: CommitmentStatusChangeRequest,
    db: Session = Depends(get_db),
):
    """Mark a commitment as completed (funded -> completed)."""
    try:
        service = CommitmentService(db)
        commitment = service.mark_completed(commitment_id, payload.updated_by)
        commitment_response = CommitmentResponse.model_validate(commitment)
        return {
            "status": "success",
            "message": "Commitment marked as completed successfully",
            "data": commitment_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark commitment as completed: {str(exc)}",
        )


@router.get(
    "/{commitment_id}/history",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def get_commitment_history(
    commitment_id: int,
    db: Session = Depends(get_db),
):
    """Get commitment history entries ordered by created_at ascending."""
    try:
        service = CommitmentService(db)
        history = service.get_commitment_history(commitment_id)
        history_response = [
            CommitmentHistoryResponse.model_validate(entry) for entry in history
        ]
        return {
            "status": "success",
            "message": "Commitment history fetched successfully",
            "data": history_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch commitment history: {str(exc)}",
        )


@router.get(
    "/summary/projects-summary",
    response_model=ProjectCommitmentsSummaryListResponse,
    status_code=status.HTTP_200_OK,
)
def get_projects_commitments_summary(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
):
    """
    Get aggregated summary of projects with their commitments.
    Returns unique projects from commitments table with:
    - Project Reference ID
    - Project Title
    - Total Commitments count
    - Status breakdown (Under_Review, Approved, Rejected, Withdrawn)
    - Total Amount (under review)
    - Best Deal (amount and interest rate)
    - Latest Commitment Date
    """
    try:
        service = ProjectService(db)
        summaries, total = service.get_projects_commitments_summary(
            skip=skip,
            limit=limit,
        )
        
        return {
            "status": "success",
            "message": "Projects commitments summary fetched successfully",
            "data": summaries,
            "total": total,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects commitments summary: {str(exc)}"
        )


@router.get(
    "/commitment-details/by-project",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def get_commitments_by_project(
    project_reference_id: str = Query(..., description="Project reference ID to filter commitments"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    include_documents: bool = Query(True, description="Include documents with file details in response (default: True)"),
    db: Session = Depends(get_db),
):
    """
    Get all commitments for a specific project by project reference ID.
    
    If `include_documents=true` (default), the response will include all documents
    with their file details from perdix_mp_files table for each commitment.
    """
    try:
        service = CommitmentService(db)
        commitments, total = service.list_commitments(
            skip=skip,
            limit=limit,
            project_reference_id=project_reference_id,
            organization_id=None,
            organization_type=None,
            status_filter=None,
        )
        
        # Build response with or without documents
        if include_documents:
            # Fetch each commitment with documents
            data = []
            for commitment in commitments:
                commitment_data = service.get_commitment_with_documents(commitment.id)
                data.append(commitment_data)
        else:
            # Just return basic commitment data
            data = [CommitmentResponse.model_validate(c).model_dump() for c in commitments]
        
        return {
            "status": "success",
            "message": f"Commitments for project {project_reference_id} fetched successfully",
            "data": data,
            "total": total,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch commitments for project: {str(exc)}"
        )


@router.post("/{commitment_id}/files/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
def upload_commitment_file(
    commitment_id: int,
    file: UploadFile = File(..., description="File to upload"),
    document_type: str = Form(..., description="Document type (sanction_letter, approval_note, kyc, terms_sheet, due_diligence)"),
    organization_id: Optional[str] = Form(None, description="Organization ID (optional, will be fetched from commitment if not provided)"),
    access_level: str = Form("private", description="Access level: public, restricted, or private"),
    is_required: bool = Form(True, description="Whether this document is required"),
    db: Session = Depends(get_db),
    uploaded_by: Optional[str] = Header(None, alias="user_id", description="User ID who uploaded the file")
):
    """
    Upload a file for an existing commitment.
    
    This endpoint:
    1. Validates the commitment exists
    2. Uploads the file using the generalized file upload service
    3. Creates a record in perdix_mp_commitment_documents table
    4. Returns the file_id and commitment_document_id
    
    **Document Types:**
    - sanction_letter: Sanction Letter
    - approval_note: Approval Note
    - kyc: KYC Documents
    - terms_sheet: Terms Sheet
    - due_diligence: Due Diligence Documents
    """
    try:
        if not uploaded_by:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID is required. Please provide user_id header."
            )
        
        service = CommitmentDocumentService(db)
        
        commitment_document = service.upload_commitment_file(
            file=file,
            commitment_id=commitment_id,
            document_type=document_type,
            uploaded_by=uploaded_by,
            organization_id=organization_id,
            access_level=access_level,
            is_required=is_required
        )
        
        return {
            "status": "success",
            "message": "Commitment file uploaded successfully",
            "data": {
                "file_id": commitment_document.file_id,
                "commitment_document_id": commitment_document.id,
                "document_type": commitment_document.document_type,
                "commitment_id": commitment_document.commitment_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Commitment file upload error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload commitment file: {str(e)}"
        )


@router.delete("/files/{file_id}", response_model=dict, status_code=status.HTTP_200_OK)
def delete_commitment_file(
    file_id: int,
    commitment_id: Optional[int] = Query(None, description="Optional commitment ID for validation"),
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(None, alias="user_id", description="User ID performing the deletion")
):
    """
    Delete a commitment file.
    
    This endpoint:
    1. Deletes the commitment document record from perdix_mp_commitment_documents
    2. Soft deletes the file using the file service
    
    **Note**: Only the user who uploaded the file can delete it.
    """
    try:
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID is required. Please provide X-User-Id header."
            )
        
        service = CommitmentDocumentService(db)
        service.delete_commitment_file(
            file_id=file_id,
            user_id=user_id,
            commitment_id=commitment_id
        )
        
        return {
            "status": "success",
            "message": "Commitment file deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Commitment file delete error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete commitment file: {str(e)}"
        )


@router.get("/{commitment_id}/documents", response_model=dict, status_code=status.HTTP_200_OK)
def get_commitment_documents(
    commitment_id: int,
    document_type: Optional[str] = Query(None, description="Filter by document type (sanction_letter, approval_note, kyc, terms_sheet, due_diligence)"),
    db: Session = Depends(get_db)
):
    """
    Get all documents for a commitment by commitment_id.
    
    This endpoint returns all documents linked to the commitment with their
    complete file details from perdix_mp_files table.
    
    Documents are returned ordered by most recent first (created_at desc).
    Only non-deleted files are included.
    
    **Query Parameters:**
    - `document_type`: Optional filter to get only specific document type
    """
    try:
        # First verify commitment exists
        commitment_service = CommitmentService(db)
        commitment = commitment_service.get_commitment_by_id(commitment_id)
        
        # Get documents with file details
        document_service = CommitmentDocumentService(db)
        documents = document_service.get_commitment_documents(
            commitment_id=commitment_id,
            document_type=document_type
        )
        
        # Build documents response with file details
        documents_response = []
        for doc in documents:
            doc_dict = {
                "id": doc.id,
                "commitment_id": doc.commitment_id,
                "file_id": doc.file_id,
                "document_type": doc.document_type,
                "is_required": doc.is_required,
                "uploaded_by": doc.uploaded_by,
                "created_at": doc.created_at,
                "created_by": doc.created_by,
                "updated_at": doc.updated_at,
                "updated_by": doc.updated_by,
            }
            
            # Include file details from perdix_mp_files if available
            if doc.file:
                doc_dict["file"] = FileResponse.model_validate(doc.file).model_dump()
            
            documents_response.append(doc_dict)
        
        return {
            "status": "success",
            "message": "Commitment documents fetched successfully",
            "data": {
                "commitment_id": commitment_id,
                "project_id": commitment.project_id,
                "documents": documents_response,
                "total": len(documents_response)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching commitment documents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch commitment documents: {str(e)}"
        )


