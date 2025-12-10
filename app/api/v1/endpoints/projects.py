from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectApproveRequest,
    ProjectRejectRequest,
    ProjectResubmitRequest,
    FullyFundedProjectListResponse,
    FullyFundedProjectResponse,
)
from app.services.project_service import ProjectService
from app.schemas.commitment import CommitmentResponse

router = APIRouter()


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_project(project_data: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project"""
    try:
        service = ProjectService(db)
        project = service.create_project(project_data)
        # Convert SQLAlchemy model to Pydantic schema
        project_response = ProjectResponse.model_validate(project)
        return {
            "status": "success",
            "message": "Project created successfully",
            "data": project_response
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("/{project_id}", response_model=dict, status_code=status.HTTP_200_OK)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get project by ID"""
    try:
        service = ProjectService(db)
        project = service.get_project_by_id(project_id)
        # Convert SQLAlchemy model to Pydantic schema
        project_response = ProjectResponse.model_validate(project)
        return {
            "status": "success",
            "message": "Project fetched successfully",
            "data": project_response
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project: {str(e)}"
        )


@router.get("/reference/{project_reference_id}", response_model=dict, status_code=status.HTTP_200_OK)
def get_project_by_reference(
    project_reference_id: str,
    committed_by: str | None = Query(
        None,
        description="If provided, returns the existing commitment data for this project and committed_by (if any)",
    ),
    db: Session = Depends(get_db),
):
    """
    Get project by reference ID.

    If `committed_by` is provided and a matching commitment exists for this
    project (based on project_reference_id and committed_by), the response
    will also include full `commitment` data embedded inside the
    ProjectResponse (under data.commitment), so the caller can directly
    use it for edit (PUT) flows.
    """
    try:
        service = ProjectService(db)
        project, commitment = service.get_project_with_commitment_by_reference(
            project_reference_id=project_reference_id,
            committed_by=committed_by,
        )

        # Convert SQLAlchemy model to Pydantic schemas
        project_response = ProjectResponse.model_validate(project)
        if commitment:
            project_response.commitment = CommitmentResponse.model_validate(commitment)

        return {
            "status": "success",
            "message": "Project fetched successfully",
            "data": project_response,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project: {str(e)}"
        )


@router.get("/", response_model=ProjectListResponse, status_code=status.HTTP_200_OK)
def get_projects(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    organization_id: str = Query(None, description="Filter by organization ID"),
    organization_type: str = Query(None, description="Filter by organization type"),
    status: str = Query(None, description="Filter by project status (draft, pending_validation, active, funding_completed, closed, rejected)"),
    user_id: str = Query(None, description="User ID to determine if projects are favorited by this user"),
    db: Session = Depends(get_db)
):
    """Get list of projects with optional filters and pagination. Projects are returned ordered by most recent first (created_at desc)."""
    try:
        service = ProjectService(db)
        projects, total = service.get_projects(
            skip=skip,
            limit=limit,
            organization_id=organization_id,
            organization_type=organization_type,
            status=status,
            user_id=user_id
        )
        # Convert SQLAlchemy models to Pydantic schemas
        projects_response = [ProjectResponse.model_validate(project) for project in projects]
        return {
            "status": "success",
            "message": "Projects fetched successfully",
            "data": projects_response,
            "total": total
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects: {str(e)}"
        )


@router.put("/{project_id}", response_model=dict, status_code=status.HTTP_200_OK)
def update_project(project_id: int, project_data: ProjectUpdate, db: Session = Depends(get_db)):
    """Update an existing project"""
    try:
        service = ProjectService(db)
        project = service.update_project(project_id, project_data)
        # Convert SQLAlchemy model to Pydantic schema
        project_response = ProjectResponse.model_validate(project)
        return {
            "status": "success",
            "message": "Project updated successfully",
            "data": project_response
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project"""
    try:
        service = ProjectService(db)
        service.delete_project(project_id)
        return {
            "status": "success",
            "message": "Project deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )


@router.post("/{project_id}/approve", response_model=dict, status_code=status.HTTP_200_OK)
def approve_project(
    project_id: int, 
    approve_data: ProjectApproveRequest, 
    db: Session = Depends(get_db)
):
    """Approve a project - sets status to 'active'"""
    try:
        service = ProjectService(db)
        project = service.approve_project(
            project_id, 
            approve_data.approved_by,
            approve_data.admin_notes
        )
        project_response = ProjectResponse.model_validate(project)
        return {
            "status": "success",
            "message": "Project approved successfully. Status set to 'active'",
            "data": project_response
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve project: {str(e)}"
        )


@router.post("/{project_id}/reject", response_model=dict, status_code=status.HTTP_200_OK)
def reject_project(
    project_id: int, 
    reject_data: ProjectRejectRequest, 
    db: Session = Depends(get_db)
):
    """Reject a project - sets status to 'rejected' and stores reject note"""
    try:
        service = ProjectService(db)
        project = service.reject_project(
            project_id, 
            reject_data.reject_note, 
            reject_data.approved_by
        )
        project_response = ProjectResponse.model_validate(project)
        return {
            "status": "success",
            "message": "Project rejected successfully. Status set to 'rejected'",
            "data": project_response
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject project: {str(e)}"
        )


@router.post("/{project_id}/resubmit", response_model=dict, status_code=status.HTTP_200_OK)
def resubmit_project(
    project_id: int,
    resubmit_data: ProjectResubmitRequest,
    db: Session = Depends(get_db)
):
    """Resubmit a rejected project - updates project fields and changes status from 'rejected' to 'pending_validation'"""
    try:
        service = ProjectService(db)
        project = service.resubmit_project(
            project_id,
            resubmit_data,
            resubmit_data.updated_by
        )
        project_response = ProjectResponse.model_validate(project)
        return {
            "status": "success",
            "message": "Project resubmitted successfully. Status changed to 'pending_validation'",
            "data": project_response
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resubmit project: {str(e)}"
        )


@router.get("/fully-funded", response_model=FullyFundedProjectListResponse, status_code=status.HTTP_200_OK)
def get_fully_funded_projects(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get list of fully funded projects (status = 'funding_completed') with funding parameters:
    - Average interest_rate from approved commitments
    - Number of investors (count of approved commitments)
    
    Only projects with status 'funding_completed' are returned.
    Funding parameters are calculated from commitments with status 'approved'.
    """
    try:
        service = ProjectService(db)
        projects, total = service.get_fully_funded_projects(
            skip=skip,
            limit=limit
        )
        # Convert SQLAlchemy models to Pydantic schemas
        projects_response = [FullyFundedProjectResponse.model_validate(project) for project in projects]
        return {
            "status": "success",
            "message": "Fully funded projects fetched successfully",
            "data": projects_response,
            "total": total
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch fully funded projects: {str(e)}"
        )

