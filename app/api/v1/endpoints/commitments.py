from fastapi import APIRouter, Depends, HTTPException, status, Query
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
from app.services.commitment_service import CommitmentService


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


@router.get(
    "/{commitment_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def get_commitment(
    commitment_id: int,
    db: Session = Depends(get_db),
):
    """Get a single commitment by ID."""
    try:
        service = CommitmentService(db)
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



