from typing import Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from fastapi import HTTPException, status
from decimal import Decimal
from datetime import datetime
from pydantic import ValidationError
from app.models.project_draft import ProjectDraft
from app.schemas.project_draft import ProjectDraftCreate, ProjectDraftUpdate
from app.core.logging import get_logger
from app.services.project_service import ProjectService
logger = get_logger("services.project_draft")


class ProjectDraftService:
    def __init__(self, db: Session):
        self.db = db
    
    def _calculate_completion_percentage(self, draft: ProjectDraft) -> Decimal:
        """Calculate completion percentage based on filled fields"""
        total_fields = 33  # Total number of main fields (24 original + 9 new fields)
        filled_fields = 0
        
        # Count filled fields
        if draft.organization_type:
            filled_fields += 1
        if draft.organization_id:
            filled_fields += 1
        if draft.title:
            filled_fields += 1
        if draft.contact_person:
            filled_fields += 1
        if draft.contact_person_designation:
            filled_fields += 1
        if draft.contact_person_email:
            filled_fields += 1
        if draft.contact_person_phone:
            filled_fields += 1
        if draft.department:
            filled_fields += 1
        if draft.category:
            filled_fields += 1
        if draft.description:
            filled_fields += 1
        if draft.start_date:
            filled_fields += 1
        if draft.end_date:
            filled_fields += 1
        # New Project Overview fields
        if draft.funding_type:
            filled_fields += 1
        if draft.commitment_allocation_days:
            filled_fields += 1
        if draft.minimum_commitment_fulfilment_percentage:
            filled_fields += 1
        if draft.mode_of_implementation:
            filled_fields += 1
        if draft.ownership:
            filled_fields += 1
        if draft.state:
            filled_fields += 1
        if draft.city:
            filled_fields += 1
        if draft.ward:
            filled_fields += 1
        if draft.total_project_cost:
            filled_fields += 1
        if draft.funding_requirement:
            filled_fields += 1
        if draft.already_secured_funds:
            filled_fields += 1
        # New Financial Information fields
        if draft.tenure:
            filled_fields += 1
        if draft.cut_off_rate_percentage:
            filled_fields += 1
        if draft.minimum_commitment_amount:
            filled_fields += 1
        if draft.conditions:
            filled_fields += 1
        if draft.fundraising_start_date:
            filled_fields += 1
        if draft.fundraising_end_date:
            filled_fields += 1
        if draft.municipality_credit_rating:
            filled_fields += 1
        if draft.municipality_credit_score:
            filled_fields += 1
        if draft.project_stage:
            filled_fields += 1
        if draft.visibility:
            filled_fields += 1
        
        percentage = (filled_fields / total_fields) * 100
        return Decimal(str(round(percentage, 2)))
    
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
    
    def create_draft(self, draft_data: ProjectDraftCreate, user_id: str = None) -> ProjectDraft:
        """Create a new project draft"""
        logger.info(f"Creating project draft")
        
        try:
            # Validate stage and visibility if provided
            if draft_data.project_stage:
                self._validate_project_stage(draft_data.project_stage)
            if draft_data.visibility:
                self._validate_visibility(draft_data.visibility)
            
            # Create draft dict
            draft_dict = draft_data.model_dump(exclude_unset=True)
            
            # Set defaults
            if 'already_secured_funds' not in draft_dict or draft_dict['already_secured_funds'] is None:
                draft_dict['already_secured_funds'] = Decimal('0')
            # Currency is always set by backend (ignore frontend value)
            draft_dict['currency'] = 'INR'
            if 'visibility' not in draft_dict or draft_dict['visibility'] is None:
                draft_dict['visibility'] = 'private'
            if 'project_stage' not in draft_dict or draft_dict['project_stage'] is None:
                draft_dict['project_stage'] = 'planning'
            
            # Set user tracking
            if user_id:
                draft_dict['created_by'] = user_id
                draft_dict['updated_by'] = user_id
            
            # Create draft
            draft = ProjectDraft(**draft_dict)
            self.db.add(draft)
            self.db.flush()  # Flush to get ID
            
            # Calculate completion percentage
            draft.completion_percentage = self._calculate_completion_percentage(draft)
            
            self.db.commit()
            self.db.refresh(draft)
            
            logger.info(f"Project draft {draft.id} created successfully")
            return draft
            
        except HTTPException:
            self.db.rollback()
            raise
        except IntegrityError as e:
            self.db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"Database integrity error creating draft: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Database constraint violation: {error_msg}"
            )
        except SQLAlchemyError as e:
            self.db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"Database error creating draft: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database error occurred. Please try again later."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating project draft: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create project draft: {str(e)}"
            )
    
    def get_draft_by_id(self, draft_id: int, user_id: str = None) -> ProjectDraft:
        """Get draft by ID"""
        query = self.db.query(ProjectDraft).filter(ProjectDraft.id == draft_id)
        
        # If user_id provided, ensure user owns the draft
        if user_id:
            query = query.filter(ProjectDraft.created_by == user_id)
        
        draft = query.first()
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project draft with ID {draft_id} not found"
            )
        return draft
    
    def get_drafts(
        self,
        user_id: str = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[list[ProjectDraft], int]:
        """Get list of drafts for a user"""
        query = self.db.query(ProjectDraft)
        
        # Filter by user if provided
        if user_id:
            query = query.filter(ProjectDraft.created_by == user_id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        drafts = query.order_by(ProjectDraft.updated_at.desc()).offset(skip).limit(limit).all()
        
        return drafts, total
    
    def update_draft(self, draft_id: int, draft_data: ProjectDraftUpdate, user_id: str = None) -> ProjectDraft:
        """Update an existing draft"""
        logger.info(f"Updating project draft {draft_id}")
        
        try:
            draft = self.get_draft_by_id(draft_id, user_id)
            
            # Get update data
            update_dict = draft_data.model_dump(exclude_unset=True)
            
            # Currency is backend-controlled - remove if frontend tries to change it
            if 'currency' in update_dict:
                logger.warning(f"Attempted to update currency for draft {draft_id}. Currency is backend-controlled and will be ignored.")
                del update_dict['currency']
            
            # Validate stage and visibility if provided
            if 'project_stage' in update_dict:
                self._validate_project_stage(update_dict['project_stage'])
            if 'visibility' in update_dict:
                self._validate_visibility(update_dict['visibility'])
            
            # Update fields
            for field, value in update_dict.items():
                setattr(draft, field, value)
            
            # Update user tracking
            if user_id:
                draft.updated_by = user_id
            draft.updated_at = datetime.now()
            
            # Recalculate completion percentage
            draft.completion_percentage = self._calculate_completion_percentage(draft)
            
            self.db.commit()
            self.db.refresh(draft)
            
            logger.info(f"Project draft {draft.id} updated successfully")
            return draft
            
        except HTTPException:
            self.db.rollback()
            raise
        except IntegrityError as e:
            self.db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"Database integrity error updating draft {draft_id}: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Database constraint violation: {error_msg}"
            )
        except SQLAlchemyError as e:
            self.db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"Database error updating draft {draft_id}: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database error occurred. Please try again later."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating project draft {draft_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update project draft: {str(e)}"
            )
    
    def delete_draft(self, draft_id: int, user_id: str = None) -> None:
        """Delete a draft"""
        logger.info(f"Deleting project draft {draft_id}")
        
        try:
            draft = self.get_draft_by_id(draft_id, user_id)
            self.db.delete(draft)
            self.db.commit()
            
            logger.info(f"Project draft {draft_id} deleted successfully")
            
        except HTTPException:
            self.db.rollback()
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"Database error deleting draft {draft_id}: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database error occurred. Please try again later."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting project draft {draft_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete project draft: {str(e)}"
            )
    
    def convert_draft_to_project_create(self, draft: ProjectDraft):
        """Convert draft to ProjectCreate schema for final submission
        
        Raises:
            HTTPException: If required fields are missing or validation fails
        """
        from app.schemas.project import ProjectCreate
        
        try:
            # Validate required fields before conversion
            required_fields = {
                'organization_type': draft.organization_type,
                'organization_id': draft.organization_id,
                'title': draft.title,
                'contact_person': draft.contact_person,
                'funding_requirement': draft.funding_requirement,
            }
            
            missing_fields = [field for field, value in required_fields.items() if not value]
            if missing_fields:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Missing required fields for submission: {', '.join(missing_fields)}. Please complete all required fields before submitting."
                )
            
            # Validate data types and constraints before conversion
            if draft.funding_requirement and draft.funding_requirement < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Funding requirement must be a positive number"
                )
            
            if draft.already_secured_funds and draft.already_secured_funds < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Already secured funds must be a positive number"
                )
            
            # Validate dates if both are provided
            if draft.start_date and draft.end_date:
                if draft.start_date > draft.end_date:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Start date cannot be after end date"
                    )
            
            if draft.fundraising_start_date and draft.fundraising_end_date:
                if draft.fundraising_start_date > draft.fundraising_end_date:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Fundraising start date cannot be after fundraising end date"
                    )
            
            # Convert draft to ProjectCreate with proper error handling
            try:
                project_data = ProjectCreate(
                    organization_type=draft.organization_type,
                    organization_id=draft.organization_id,
                    title=draft.title,
                    department=draft.department,
                    contact_person=draft.contact_person,
                    contact_person_designation=draft.contact_person_designation,
                    contact_person_email=draft.contact_person_email,
                    contact_person_phone=draft.contact_person_phone,
                    category=draft.category,
                    project_stage=draft.project_stage or 'planning',
                    description=draft.description,
                    start_date=draft.start_date,
                    end_date=draft.end_date,
                    # New Project Overview fields
                    funding_type=draft.funding_type,
                    commitment_allocation_days=draft.commitment_allocation_days,
                    commitment_gap=draft.commitment_gap,
                    minimum_commitment_fulfilment_percentage=draft.minimum_commitment_fulfilment_percentage,
                    mode_of_implementation=draft.mode_of_implementation,
                    ownership=draft.ownership,
                    state=draft.state,
                    city=draft.city,
                    ward=draft.ward,
                    total_project_cost=draft.total_project_cost,
                    funding_requirement=draft.funding_requirement,
                    already_secured_funds=draft.already_secured_funds or Decimal('0'),
                    currency='INR',  # Always set by backend
                    # New Financial Information fields
                    tenure=draft.tenure,
                    cut_off_rate_percentage=draft.cut_off_rate_percentage,
                    minimum_commitment_amount=draft.minimum_commitment_amount,
                    conditions=draft.conditions,
                    fundraising_start_date=draft.fundraising_start_date,
                    fundraising_end_date=draft.fundraising_end_date,
                    municipality_credit_rating=draft.municipality_credit_rating,
                    municipality_credit_score=draft.municipality_credit_score,
                    status='pending_validation',  # Set status for submitted project
                    visibility=draft.visibility or 'private',
                    approved_by=draft.approved_by,
                    admin_notes=draft.admin_notes,
                    created_by=draft.created_by,
                )
            except ValidationError as e:
                # Handle Pydantic validation errors
                error_messages = []
                for error in e.errors():
                    field = '.'.join(str(loc) for loc in error['loc'])
                    error_messages.append(f"{field}: {error['msg']}")
                
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Validation error: {', '.join(error_messages)}"
                )
            
            return project_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error converting draft {draft.id} to project: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to convert draft to project: {str(e)}"
            )
    
    def submit_draft(self, draft_id: int, user_id: str = None):
        """Submit draft - converts to project and deletes draft
        
        This method handles the complete submission flow with proper error handling:
        1. Validates draft exists and user has access
        2. Converts draft to ProjectCreate schema
        3. Creates project using ProjectService
        4. Deletes draft only after successful project creation
        
        Raises:
            HTTPException: If any step fails
        """
        draft = None
        project = None
        
        try:
            # Step 1: Get and validate draft
            draft = self.get_draft_by_id(draft_id, user_id=user_id)
            logger.info(f"Submitting draft {draft_id} for user {user_id}")
            
            # Step 2: Convert draft to ProjectCreate schema
            # This validates required fields and data types
            project_data = self.convert_draft_to_project_create(draft)
            
            # Step 3: Create project using ProjectService
            # Import here to avoid circular dependency
           
            project_service = ProjectService(self.db)
            
            try:
                project = project_service.create_project(project_data)
                logger.info(f"Project {project.id} created successfully from draft {draft_id}")
            except HTTPException as e:
                # Re-raise HTTPExceptions from project creation (validation errors, etc.)
                logger.warning(f"Project creation failed for draft {draft_id}: {e.detail}")
                raise
            except IntegrityError as e:
                # Handle database constraint violations
                self.db.rollback()
                error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
                
                # Check for specific constraint violations
                if 'project_reference_id' in error_msg.lower() or 'unique' in error_msg.lower():
                    logger.error(f"Duplicate project reference ID detected for draft {draft_id}")
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="A project with this reference ID already exists. Please try again."
                    )
                else:
                    logger.error(f"Database integrity error creating project from draft {draft_id}: {error_msg}")
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Database constraint violation: {error_msg}"
                    )
            except SQLAlchemyError as e:
                # Handle other database errors
                self.db.rollback()
                error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
                logger.error(f"Database error creating project from draft {draft_id}: {error_msg}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database error occurred while creating project. Please try again later."
                )
            except Exception as e:
                # Handle any other unexpected errors during project creation
                self.db.rollback()
                logger.error(f"Unexpected error creating project from draft {draft_id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create project: {str(e)}"
                )
            
            # Step 4: Delete draft only after successful project creation
            # If deletion fails, log but don't fail the request (project is already created)
            try:
                self.delete_draft(draft_id, user_id=user_id)
                logger.info(f"Draft {draft_id} deleted successfully after project creation")
            except Exception as e:
                # Log error but don't fail - project is already created
                logger.warning(f"Failed to delete draft {draft_id} after project creation: {str(e)}")
                logger.warning(f"Draft {draft_id} should be manually cleaned up. Project {project.id} was created successfully.")
                # Don't raise - project creation was successful
            
            return project
            
        except HTTPException:
            # Re-raise HTTPExceptions (validation errors, not found, etc.)
            raise
        except Exception as e:
            # Handle any unexpected errors
            self.db.rollback()
            logger.error(f"Unexpected error submitting draft {draft_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to submit draft: {str(e)}"
            )

