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


@router.get("/{favorite_id}", response_model=dict, status_code=status.HTTP_200_OK)
def get_project_favorite(favorite_id: int, db: Session = Depends(get_db)):
    """Get project favorite by ID"""
    try:
        service = ProjectFavoriteService(db)
        favorite = service.get_favorite_by_id(favorite_id)
        # Convert SQLAlchemy model to Pydantic schema
        favorite_response = ProjectFavoriteResponse.model_validate(favorite)
        return {
            "status": "success",
            "message": "Project favorite fetched successfully",
            "data": favorite_response
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project favorite: {str(e)}"
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


@router.delete("/{favorite_id}", status_code=status.HTTP_200_OK)
def delete_project_favorite(favorite_id: int, db: Session = Depends(get_db)):
    """Delete a project favorite by ID"""
    try:
        service = ProjectFavoriteService(db)
        service.delete_project_favorite(favorite_id)
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

