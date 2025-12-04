from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.project_favorite import ProjectFavoriteCreate, ProjectFavoriteUpdate, ProjectFavoriteResponse
from app.services.project_favorite_service import ProjectFavoriteService

router = APIRouter()


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_project_favorite(favorite_data: ProjectFavoriteCreate, db: Session = Depends(get_db)):
    """Create a new project favorite"""
    try:
        service = ProjectFavoriteService(db)
        favorite = service.create_project_favorite(favorite_data)
        # Convert SQLAlchemy model to Pydantic schema
        favorite_response = ProjectFavoriteResponse.model_validate(favorite)
        return {
            "status": "success",
            "message": "Project favorited successfully",
            "data": favorite_response
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project favorite: {str(e)}"
        )




@router.get("/", response_model=dict, status_code=status.HTTP_200_OK)
def get_project_favorites(
    user_id: str = Query(..., description="User ID to get favorites for"),
    organization_id: str = Query(None, description="Filter by organization ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Get list of project favorites for a user"""
    try:
        service = ProjectFavoriteService(db)
        favorites, total = service.get_favorites_by_user(
            user_id=user_id,
            organization_id=organization_id,
            skip=skip,
            limit=limit
        )
        # Convert SQLAlchemy models to Pydantic schemas
        favorites_response = [ProjectFavoriteResponse.model_validate(favorite) for favorite in favorites]
        return {
            "status": "success",
            "message": "Project favorites fetched successfully",
            "data": favorites_response,
            "total": total
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project favorites: {str(e)}"
        )




@router.get("/project-details", response_model=dict, status_code=status.HTTP_200_OK)
def get_favorited_project_details(
    user_id: str = Query(..., description="User ID to get favorited project details for"),
    organization_id: str | None = Query(None, description="Filter by organization ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
):
    """
    Get detailed project records from perdix_mp_projects for all projects
    favorited by the given user (and optionally filtered by organization).
    """
    try:
        service = ProjectFavoriteService(db)
        projects, total = service.get_favorited_project_details(
            user_id=user_id,
            organization_id=organization_id,
            skip=skip,
            limit=limit,
        )

        return {
            "status": "success",
            "message": "Favorited project details fetched successfully",
            "data": projects,
            "total": total,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch favorited project details: {str(e)}",
        )

@router.delete("/", status_code=status.HTTP_200_OK)
def delete_project_favorite_by_project_and_user(
    project_reference_id: str = Query(..., description="Project reference ID"),
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Delete a project favorite by project_reference_id and user_id"""
    try:
        service = ProjectFavoriteService(db)
        service.delete_project_favorite_by_project_and_user(project_reference_id, user_id)
        return {
            "status": "success",
            "message": "Project favorite deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project favorite: {str(e)}"
        )
