from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Header
from typing import Optional
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional
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
from app.services.project_document_service import ProjectDocumentService
from app.schemas.commitment import CommitmentResponse
from app.core.logging import get_logger

logger = get_logger("api.projects")

router = APIRouter()


@router.post("/files/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
def upload_project_file(
    file: UploadFile = File(..., description="File to upload"),
    project_reference_id: Optional[str] = Form(None, description="Project reference ID (if draft/project exists)"),
    draft_id: Optional[int] = Form(None, description="Draft ID (alternative to project_reference_id)"),
    document_type: str = Form(..., description="Document type (dpr, feasibility_study, compliance_certificate, budget_approval, tender_rfp, project_image, optional_media)"),
    organization_id: str = Form(..., description="Organization ID"),
    access_level: str = Form("public", description="Access level: public, restricted, or private"),
    auto_create_draft: bool = Form(True, description="Auto-create draft if project_reference_id doesn't exist"),
    db: Session = Depends(get_db),
    uploaded_by: Optional[str] = Header(None, alias="user_id", description="User ID who uploaded the file")
):
    """
    Upload a file for a project or draft.
    
    This endpoint:
    1. Accepts either project_reference_id OR draft_id
    2. If project_reference_id provided, uses that
    3. If draft_id provided, fetches draft's project_reference_id
    4. If neither exists and auto_create_draft=True, generates project_reference_id and creates draft
    5. Uploads the file using the generalized file upload service
    6. Creates a record in perdix_mp_project_documents table
    7. Returns the file_id and project_document_id
    
    **Document Types:**
    - dpr: Detailed Project Report
    - feasibility_study: Feasibility Study
    - compliance_certificate: Compliance Certificate
    - budget_approval: Budget Approval
    - tender_rfp: Tender/RFP
    - project_image: Project Image
    - optional_media: Optional Media Files
    
    **Note**: The file_id returned should be used by the frontend to include in project creation/update payloads.
    """
    try:
        if not uploaded_by:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID is required. Please provide user_id header."
            )
        
        service = ProjectDocumentService(db)
        
        # If draft_id provided, get its project_reference_id
        if draft_id and not project_reference_id:
            from app.services.project_draft_service import ProjectDraftService
            draft_service = ProjectDraftService(db)
            draft = draft_service.get_draft_by_id(draft_id, user_id=uploaded_by)
            project_reference_id = draft.project_reference_id
            if not project_reference_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Draft {draft_id} does not have a project_reference_id"
                )
        
        # If project_reference_id still not provided, generate one
        if not project_reference_id:
            from app.services.project_service import ProjectService
            project_service = ProjectService(db)
            project_reference_id = project_service._generate_project_reference_id()
            project_service._validate_project_reference_id_unique(project_reference_id)
            logger.info(f"Generated project_reference_id for file upload: {project_reference_id}")
        
        project_document = service.upload_project_file(
            file=file,
            project_reference_id=project_reference_id,
            document_type=document_type,
            uploaded_by=uploaded_by,
            organization_id=organization_id,
            access_level=access_level,
            auto_create_draft=auto_create_draft
        )
        
        return {
            "status": "success",
            "message": "Project file uploaded successfully",
            "data": {
                "file_id": project_document.file_id,
                "project_document_id": project_document.id,
                "document_type": project_document.document_type,
                "project_reference_id": project_document.project_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Project file upload error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload project file: {str(e)}"
        )


@router.delete("/files/{file_id}", response_model=dict, status_code=status.HTTP_200_OK)
def delete_project_file(
    file_id: int,
    project_reference_id: Optional[str] = Query(None, description="Optional project reference ID for validation"),
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(None, alias="user_id", description="User ID performing the deletion")
):
    """
    Delete a project file.
    
    This endpoint:
    1. Deletes the project document record from perdix_mp_project_documents
    2. Soft deletes the file using the file service
    
    **Note**: Only the user who uploaded the file can delete it.
    """
    try:
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID is required. Please provide X-User-Id header."
            )
        
        service = ProjectDocumentService(db)
        service.delete_project_file(
            file_id=file_id,
            user_id=user_id,
            project_reference_id=project_reference_id
        )
        
        return {
            "status": "success",
            "message": "Project file deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Project file delete error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project file: {str(e)}"
        )


@router.get("/reference/{project_reference_id}/documents", response_model=dict, status_code=status.HTTP_200_OK)
def get_project_documents(
    project_reference_id: str,
    document_type: Optional[str] = Query(None, description="Filter by document type (dpr, feasibility_study, compliance_certificate, budget_approval, tender_rfp, project_image, optional_media)"),
    db: Session = Depends(get_db)
):
    """
    Get all documents for a project by project_reference_id.
    
    This endpoint returns all documents linked to the project with their
    complete file details from perdix_mp_files table.
    
    Documents are returned ordered by most recent first (created_at desc).
    Only non-deleted files are included.
    
    **Query Parameters:**
    - `document_type`: Optional filter to get only specific document type
    """
    try:
        # First verify project exists
        project_service = ProjectService(db)
        project = project_service.get_project_by_reference_id(project_reference_id)
        
        # Get documents with file details
        document_service = ProjectDocumentService(db)
        documents = document_service.get_project_documents(
            project_reference_id=project_reference_id,
            document_type=document_type
        )
        
        # Build documents response with file details
        documents_response = []
        for doc in documents:
            doc_dict = {
                "id": doc.id,
                "project_id": doc.project_id,
                "file_id": doc.file_id,
                "document_type": doc.document_type,
                "version": doc.version,
                "access_level": doc.access_level,
                "uploaded_by": doc.uploaded_by,
                "created_at": doc.created_at,
                "created_by": doc.created_by,
                "updated_at": doc.updated_at,
                "updated_by": doc.updated_by,
            }
            
            # Include file details from perdix_mp_files if available
            if doc.file:
                from app.schemas.file import FileResponse
                doc_dict["file"] = FileResponse.model_validate(doc.file).model_dump()
            
            documents_response.append(doc_dict)
        
        return {
            "status": "success",
            "message": "Project documents fetched successfully",
            "data": {
                "project_reference_id": project_reference_id,
                "project_title": project.title,
                "documents": documents_response,
                "total": len(documents_response)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project documents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project documents: {str(e)}"
        )


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


@router.get("/funded-by-user", response_model=ProjectListResponse, status_code=status.HTTP_200_OK)
def get_projects_funded_by_user(
    committed_by: str = Query(..., description="User ID who has made commitments to projects"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get all projects that have been funded by a specific user.
    
    This endpoint returns all projects where the user (committed_by) has made
    at least one commitment. Projects are fetched using project_reference_id from
    the projects table, joined with commitments table where committed_by matches
    the provided user ID.
    
    For each project, the response includes the latest commitment details (including
    commitment status) made by the user, attached under the 'commitment' field.
    
    Projects are returned ordered by most recent first (created_at desc).
    """
    try:
        service = ProjectService(db)
        projects, total = service.get_projects_funded_by_user(
            committed_by=committed_by,
            skip=skip,
            limit=limit
        )
        # Convert SQLAlchemy models to Pydantic schemas
        # ProjectResponse schema already supports commitment field
        projects_response = [ProjectResponse.model_validate(project) for project in projects]
        return {
            "status": "success",
            "message": f"Projects funded by user {committed_by} fetched successfully",
            "data": projects_response,
            "total": total
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects funded by user: {str(e)}"
        )


@router.get("/states", response_model=dict, status_code=status.HTTP_200_OK)
def get_distinct_states(db: Session = Depends(get_db)):
    """Get all distinct states from projects table, ordered alphabetically."""
    try:
        service = ProjectService(db)
        states = service.get_distinct_states()
        return {
            "status": "success",
            "message": "Distinct states fetched successfully",
            "data": states
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch distinct states: {str(e)}"
        )


@router.get("/value-ranges", response_model=dict, status_code=status.HTTP_200_OK)
def get_value_ranges(db: Session = Depends(get_db)):
    """Get min and max ranges for funding_requirement and commitment_gap fields."""
    try:
        service = ProjectService(db)
        ranges = service.get_value_ranges()
        return {
            "status": "success",
            "message": "Value ranges fetched successfully",
            "data": ranges
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch value ranges: {str(e)}"
        )


@router.get("/municipality-credit-ratings", response_model=dict, status_code=status.HTTP_200_OK)
def get_distinct_municipality_credit_ratings(db: Session = Depends(get_db)):
    """Get all distinct municipality_credit_rating values from projects table, ordered alphabetically."""
    try:
        service = ProjectService(db)
        ratings = service.get_distinct_municipality_credit_ratings()
        return {
            "status": "success",
            "message": "Distinct municipality credit ratings fetched successfully",
            "data": ratings
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch distinct municipality credit ratings: {str(e)}"
        )


@router.get("/{project_id}", response_model=dict, status_code=status.HTTP_200_OK)
def get_project(
    project_id: int,
    include_documents: bool = Query(False, description="Include documents with file details in response"),
    db: Session = Depends(get_db)
):
    """
    Get project by ID.
    
    If `include_documents=true`, the response will include all documents
    with their file details from perdix_mp_files table.
    """
    try:
        service = ProjectService(db)
        
        if include_documents:
            project_data = service.get_project_with_documents(project_id=project_id)
            return {
                "status": "success",
                "message": "Project fetched successfully",
                "data": project_data
            }
        else:
            project = service.get_project_by_id(project_id)
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
    include_documents: bool = Query(False, description="Include documents with file details in response"),
    db: Session = Depends(get_db),
):
    """
    Get project by reference ID.

    If `committed_by` is provided and a matching commitment exists for this
    project (based on project_reference_id and committed_by), the response
    will also include full `commitment` data embedded inside the
    ProjectResponse (under data.commitment), so the caller can directly
    use it for edit (PUT) flows.
    
    If `include_documents=true`, the response will include all documents
    with their file details from perdix_mp_files table.
    """
    try:
        service = ProjectService(db)
        
        if include_documents:
            project_data = service.get_project_with_documents(project_reference_id=project_reference_id)
            
            # If committed_by is provided, add commitment data
            if committed_by:
                project, commitment = service.get_project_with_commitment_by_reference(
                    project_reference_id=project_reference_id,
                    committed_by=committed_by,
                )
                if commitment:
                    project_data["commitment"] = CommitmentResponse.model_validate(commitment).model_dump()
            
            return {
                "status": "success",
                "message": "Project fetched successfully",
                "data": project_data,
            }
        else:
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
    state: str = Query(None, description="Filter by state"),
    user_id: str = Query(None, description="User ID to determine if projects are favorited by this user"),
    search: str = Query(None, description="Search by project reference ID"),
    states: str = Query(None, description="Filter by state name"),
    categories: str = Query(None, description="Filter by project category"),
    project_stage: str = Query(None, description="Filter by project stage (planning, initiated, in_progress)"),
    municipality_credit_rating: str = Query(None, description="Filter by credit rating"),
    funding_type: str = Query(None, description="Filter by funding type"),
    mode_of_implementation: str = Query(None, description="Filter by implementation mode"),
    ownership: str = Query(None, description="Filter by ownership type"),
    min_funding_requirement: Optional[Decimal] = Query(None, description="Minimum funding requirement (in rupees)"),
    max_funding_requirement: Optional[Decimal] = Query(None, description="Maximum funding requirement (in rupees)"),
    min_commitment_gap: Optional[Decimal] = Query(None, description="Minimum commitment gap (in rupees)"),
    max_commitment_gap: Optional[Decimal] = Query(None, description="Maximum commitment gap (in rupees)"),
    min_total_project_cost: Optional[Decimal] = Query(None, description="Minimum project cost (in rupees)"),
    max_total_project_cost: Optional[Decimal] = Query(None, description="Maximum project cost (in rupees)"),
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
            state=state,
            user_id=user_id,
            search=search,
            states=states,
            categories=categories,
            project_stage=project_stage,
            municipality_credit_rating=municipality_credit_rating,
            funding_type=funding_type,
            mode_of_implementation=mode_of_implementation,
            ownership=ownership,
            min_funding_requirement=min_funding_requirement,
            max_funding_requirement=max_funding_requirement,
            min_commitment_gap=min_commitment_gap,
            max_commitment_gap=max_commitment_gap,
            min_total_project_cost=min_total_project_cost,
            max_total_project_cost=max_total_project_cost
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

