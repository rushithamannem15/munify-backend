from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from app.services.project_service import ProjectService

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
def get_project_by_reference(project_reference_id: str, db: Session = Depends(get_db)):
    """Get project by reference ID"""
    try:
        service = ProjectService(db)
        project = service.get_project_by_reference_id(project_reference_id)
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


@router.get("/", response_model=ProjectListResponse, status_code=status.HTTP_200_OK)
def get_projects(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    organization_id: str = Query(None, description="Filter by organization ID"),
    organization_type: str = Query(None, description="Filter by organization type"),
    status: str = Query(None, description="Filter by project status"),
    visibility: str = Query(None, description="Filter by project visibility"),
    db: Session = Depends(get_db)
):
    """Get list of projects with optional filters and pagination"""
    try:
        service = ProjectService(db)
        projects, total = service.get_projects(
            skip=skip,
            limit=limit,
            organization_id=organization_id,
            organization_type=organization_type,
            status=status,
            visibility=visibility
        )
        # Convert SQLAlchemy models to Pydantic schemas
        projects_response = [ProjectResponse.model_validate(project) for project in projects]
        return {
            "status": "success",
            "message": "Projects fetched successfully",
            "data": projects_response,
            "total": total
        }
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

