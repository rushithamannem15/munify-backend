from typing import Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models.project_favorite import ProjectFavorite
from app.models.project import Project
from app.schemas.project_favorite import ProjectFavoriteCreate, ProjectFavoriteUpdate
from app.core.logging import get_logger

logger = get_logger("services.project_favorite")


class ProjectFavoriteService:
    def __init__(self, db: Session):
        self.db = db
    
    def _validate_project_exists(self, project_reference_id: str) -> Project:
        """Validate that project exists by project_reference_id"""
        project = self.db.query(Project).filter(Project.project_reference_id == project_reference_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with reference ID '{project_reference_id}' not found"
            )
        return project
    
    def _check_duplicate_favorite(self, project_reference_id: str, organization_id: str, user_id: str) -> bool:
        """Check if favorite already exists"""
        existing = self.db.query(ProjectFavorite).filter(
            ProjectFavorite.project_reference_id == project_reference_id,
            ProjectFavorite.organization_id == organization_id,
            ProjectFavorite.user_id == user_id
        ).first()
        return existing is not None
    
    def create_project_favorite(self, favorite_data: ProjectFavoriteCreate) -> ProjectFavorite:
        """Create a new project favorite"""
        logger.info(f"Creating project favorite for project {favorite_data.project_reference_id}, user {favorite_data.user_id}, org {favorite_data.organization_id}")
        
        try:
            # Validate project exists
            self._validate_project_exists(favorite_data.project_reference_id)
            
            # Check for duplicate favorite
            if self._check_duplicate_favorite(
                favorite_data.project_reference_id,
                favorite_data.organization_id,
                favorite_data.user_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Project is already favorited by this user in this organization"
                )
            
            # Create favorite
            favorite_dict = favorite_data.model_dump(exclude_unset=True)
            favorite = ProjectFavorite(**favorite_dict)
            self.db.add(favorite)
            self.db.commit()
            self.db.refresh(favorite)
            
            logger.info(f"Project favorite {favorite.id} created successfully")
            return favorite
            
        except HTTPException:
            self.db.rollback()
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating project favorite: {str(e)}")
            # Check if it's a unique constraint violation
            if "uq_project_favorite_org_user" in str(e.orig) or "UNIQUE" in str(e.orig):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Project is already favorited by this user in this organization"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Database constraint violation: {str(e)}"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating project favorite: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create project favorite: {str(e)}"
            )
    
    def get_favorite_by_id(self, favorite_id: int) -> ProjectFavorite:
        """Get project favorite by ID"""
        favorite = self.db.query(ProjectFavorite).filter(ProjectFavorite.id == favorite_id).first()
        if not favorite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project favorite with ID {favorite_id} not found"
            )
        return favorite
    
    def get_favorites_by_user(
        self,
        user_id: str,
        organization_id: str = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[list[ProjectFavorite], int]:
        """Get list of project favorites for a user"""
        query = self.db.query(ProjectFavorite).filter(ProjectFavorite.user_id == user_id)
        
        if organization_id:
            query = query.filter(ProjectFavorite.organization_id == organization_id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        favorites = query.offset(skip).limit(limit).all()
        
        return favorites, total
    
    def delete_project_favorite(self, favorite_id: int) -> None:
        """Delete a project favorite"""
        logger.info(f"Deleting project favorite {favorite_id}")
        
        try:
            favorite = self.get_favorite_by_id(favorite_id)
            self.db.delete(favorite)
            self.db.commit()
            
            logger.info(f"Project favorite {favorite_id} deleted successfully")
            
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting project favorite: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete project favorite: {str(e)}"
            )

