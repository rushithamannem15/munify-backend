from typing import Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from decimal import Decimal
from datetime import datetime
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.core.logging import get_logger

logger = get_logger("services.project")


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
    
    def _generate_project_reference_id(self) -> str:
        """Generate unique project reference ID: PROJ-YYYY-XXXXX"""
        current_year = datetime.now().year
        
        # Get the count of projects created this year
        count_query = self.db.query(func.count(Project.id)).filter(
            func.extract('year', Project.created_at) == current_year
        )
        count = count_query.scalar() or 0
        
        # Format: PROJ-YYYY-XXXXX (5 digits, zero-padded)
        sequence = str(count + 1).zfill(5)
        return f"PROJ-{current_year}-{sequence}"
    
    def _validate_project_reference_id_unique(self, project_reference_id: str, exclude_id: int = None):
        """Validate that project_reference_id is unique"""
        query = self.db.query(Project).filter(Project.project_reference_id == project_reference_id)
        if exclude_id:
            query = query.filter(Project.id != exclude_id)
        existing = query.first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project reference ID '{project_reference_id}' already exists"
            )
    
    def _validate_status(self, status_value: str):
        """Validate project status"""
        valid_statuses = ['draft', 'pending_validation', 'active', 'funding_completed', 'closed', 'rejected']
        if status_value and status_value not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
    
    def _validate_project_stage(self, stage: str):
        """Validate project stage"""
        valid_stages = ['planning', 'initiated', 'in_progress']
        if stage and stage not in valid_stages:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid project stage. Must be one of: {', '.join(valid_stages)}"
            )
    
    def _validate_visibility(self, visibility: str):
        """Validate project visibility"""
        valid_visibilities = ['private', 'public']
        if visibility and visibility not in valid_visibilities:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid visibility. Must be one of: {', '.join(valid_visibilities)}"
            )
    
    def create_project(self, project_data: ProjectCreate) -> Project:
        """Create a new project"""
        logger.info(f"Creating project: {project_data.title}")
        
        try:
            # Validate status, stage, and visibility
            self._validate_status(project_data.status)
            self._validate_project_stage(project_data.project_stage)
            self._validate_visibility(project_data.visibility)
            
            # Generate project reference ID
            project_reference_id = self._generate_project_reference_id()
            self._validate_project_reference_id_unique(project_reference_id)
            
            # Create project
            project_dict = project_data.model_dump(exclude_unset=True)
            project_dict['project_reference_id'] = project_reference_id
            
            # Set defaults
            if 'already_secured_funds' not in project_dict or project_dict['already_secured_funds'] is None:
                project_dict['already_secured_funds'] = Decimal('0')
            if 'currency' not in project_dict or project_dict['currency'] is None:
                project_dict['currency'] = 'INR'
            if 'status' not in project_dict or project_dict['status'] is None:
                project_dict['status'] = 'draft'
            if 'visibility' not in project_dict or project_dict['visibility'] is None:
                project_dict['visibility'] = 'private'
            if 'project_stage' not in project_dict or project_dict['project_stage'] is None:
                project_dict['project_stage'] = 'planning'
            if 'funding_raised' not in project_dict or project_dict['funding_raised'] is None:
                project_dict['funding_raised'] = Decimal('0')
            
            project = Project(**project_dict)
            self.db.add(project)
            self.db.commit()
            self.db.refresh(project)
            
            logger.info(f"Project {project.id} created successfully with reference ID: {project.project_reference_id}")
            return project
            
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating project: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create project: {str(e)}"
            )
    
    def get_project_by_id(self, project_id: int) -> Project:
        """Get project by ID"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        return project
    
    def get_project_by_reference_id(self, project_reference_id: str) -> Project:
        """Get project by reference ID"""
        project = self.db.query(Project).filter(Project.project_reference_id == project_reference_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with reference ID '{project_reference_id}' not found"
            )
        return project
    
    def get_projects(
        self,
        skip: int = 0,
        limit: int = 100,
        organization_id: str = None,
        organization_type: str = None,
        status: str = None,
        visibility: str = None
    ) -> Tuple[list[Project], int]:
        """Get list of projects with optional filters"""
        query = self.db.query(Project)
        
        # Apply filters
        if organization_id:
            query = query.filter(Project.organization_id == organization_id)
        if organization_type:
            query = query.filter(Project.organization_type == organization_type)
        if status:
            query = query.filter(Project.status == status)
        if visibility:
            query = query.filter(Project.visibility == visibility)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
        
        return projects, total
    
    def update_project(self, project_id: int, project_data: ProjectUpdate) -> Project:
        """Update an existing project"""
        logger.info(f"Updating project {project_id}")
        
        try:
            project = self.get_project_by_id(project_id)
            
            # Validate status, stage, and visibility if provided
            update_dict = project_data.model_dump(exclude_unset=True)
            
            if 'status' in update_dict:
                self._validate_status(update_dict['status'])
            if 'project_stage' in update_dict:
                self._validate_project_stage(update_dict['project_stage'])
            if 'visibility' in update_dict:
                self._validate_visibility(update_dict['visibility'])
            
            # Update fields
            for field, value in update_dict.items():
                setattr(project, field, value)
            
            # Update updated_at timestamp
            project.updated_at = datetime.now()
            
            self.db.commit()
            self.db.refresh(project)
            
            logger.info(f"Project {project.id} updated successfully")
            return project
            
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating project {project_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update project: {str(e)}"
            )
    
    def delete_project(self, project_id: int) -> None:
        """Delete a project"""
        logger.info(f"Deleting project {project_id}")
        
        try:
            project = self.get_project_by_id(project_id)
            self.db.delete(project)
            self.db.commit()
            
            logger.info(f"Project {project_id} deleted successfully")
            
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting project {project_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete project: {str(e)}"
            )

