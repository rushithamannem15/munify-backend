from typing import Tuple, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from fastapi import HTTPException, status
from decimal import Decimal
from datetime import datetime
from app.models.project import Project
from app.models.project_favorite import ProjectFavorite
from app.models.project_rejection_history import ProjectRejectionHistory
from app.models.commitment import Commitment
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.core.logging import get_logger
from app.models.project_draft import ProjectDraft
logger = get_logger("services.project")


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
    
    def _generate_project_reference_id(self) -> str:
        """Generate unique project reference ID: PROJ-YYYY-XXXXX
        Counts both projects and drafts to ensure uniqueness across both tables.
        """
       
        
        current_year = datetime.now().year
        
        # Count projects created this year
        project_count = self.db.query(func.count(Project.id)).filter(
            func.extract('year', Project.created_at) == current_year
        ).scalar() or 0
        
        # Count drafts created this year (with project_reference_id)
        draft_count = self.db.query(func.count(ProjectDraft.id)).filter(
            ProjectDraft.project_reference_id.isnot(None),
            func.extract('year', ProjectDraft.created_at) == current_year
        ).scalar() or 0
        
        # Total count = projects + drafts
        total_count = project_count + draft_count
        
        # Format: PROJ-YYYY-XXXXX (5 digits, zero-padded)
        sequence = str(total_count + 1).zfill(5)
        return f"PROJ-{current_year}-{sequence}"
    
    def _validate_project_reference_id_unique(
        self, 
        project_reference_id: str, 
        exclude_id: int = None, 
        exclude_draft_id: int = None
    ):
        """Validate that project_reference_id is unique across both projects and drafts"""
        
        
        # Check in projects table
        query = self.db.query(Project).filter(Project.project_reference_id == project_reference_id)
        if exclude_id:
            query = query.filter(Project.id != exclude_id)
        existing_project = query.first()
        
        if existing_project:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project reference ID '{project_reference_id}' already exists in projects"
            )
        
        # Check in drafts table
        draft_query = self.db.query(ProjectDraft).filter(ProjectDraft.project_reference_id == project_reference_id)
        if exclude_draft_id:
            draft_query = draft_query.filter(ProjectDraft.id != exclude_draft_id)
        existing_draft = draft_query.first()
        
        if existing_draft:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project reference ID '{project_reference_id}' already exists in drafts"
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
    
    def create_project(self, project_data: ProjectCreate, project_reference_id: Optional[str] = None) -> Project:
        """Create a new project
        
        Args:
            project_data: Project creation data
            project_reference_id: Optional existing project_reference_id (from draft). 
                                 If provided, uses this ID instead of generating a new one.
        """
        logger.info(f"Creating project: {project_data.title}")
        
        try:
            # Validate status, stage, and visibility
            self._validate_status(project_data.status)
            self._validate_project_stage(project_data.project_stage)
            self._validate_visibility(project_data.visibility)
            
            # Use existing project_reference_id if provided, otherwise generate new one
            if project_reference_id:
                # When project_reference_id is provided, it comes from a draft submission.
                # We only need to check if it exists in projects table (not drafts, 
                # because it MUST exist in the draft being submitted).
                existing_project = self.db.query(Project).filter(
                    Project.project_reference_id == project_reference_id
                ).first()
                
                if existing_project:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Project reference ID '{project_reference_id}' already exists in projects"
                    )
                
                final_project_reference_id = project_reference_id
                logger.info(f"Using existing project_reference_id: {final_project_reference_id}")
            else:
                # Generate new project reference ID
                final_project_reference_id = self._generate_project_reference_id()
                self._validate_project_reference_id_unique(final_project_reference_id)
                logger.info(f"Generated new project_reference_id: {final_project_reference_id}")
            
            # Create project
            project_dict = project_data.model_dump(exclude_unset=True)
            project_dict['project_reference_id'] = final_project_reference_id
            
            # Set defaults
            if 'already_secured_funds' not in project_dict or project_dict['already_secured_funds'] is None:
                project_dict['already_secured_funds'] = Decimal('0')
            # Currency is always set by backend (ignore frontend value)
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
    
    def get_project_with_documents(self, project_id: int = None, project_reference_id: str = None) -> dict:
        """
        Get project by ID or reference ID with associated documents and file details.
        
        This method joins perdix_mp_project_documents and perdix_mp_files tables
        to return complete file information for all documents linked to the project.
        
        Args:
            project_id: Project ID (alternative to project_reference_id)
            project_reference_id: Project reference ID (alternative to project_id)
            
        Returns:
            Dictionary containing project data and documents with file details
        """
        from app.services.project_document_service import ProjectDocumentService
        
        # Get project
        if project_id:
            project = self.get_project_by_id(project_id)
        elif project_reference_id:
            project = self.get_project_by_reference_id(project_reference_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either project_id or project_reference_id must be provided"
            )
        
        # Get documents with file details using ProjectDocumentService
        documents_data = []
        if project.project_reference_id:
            document_service = ProjectDocumentService(self.db)
            documents = document_service.get_project_documents(
                project_reference_id=project.project_reference_id
            )
            
            # Build documents response with file details
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
                    file_dict = {
                        "id": doc.file.id,
                        "organization_id": doc.file.organization_id,
                        "uploaded_by": doc.file.uploaded_by,
                        "filename": doc.file.filename,
                        "original_filename": doc.file.original_filename,
                        "mime_type": doc.file.mime_type,
                        "file_size": doc.file.file_size,
                        "storage_path": doc.file.storage_path,
                        "checksum": doc.file.checksum,
                        "access_level": doc.file.access_level,
                        "download_count": doc.file.download_count,
                        "is_deleted": doc.file.is_deleted,
                        "deleted_at": doc.file.deleted_at,
                        "created_at": doc.file.created_at,
                        "created_by": doc.file.created_by,
                        "updated_at": doc.file.updated_at,
                        "updated_by": doc.file.updated_by,
                    }
                    doc_dict["file"] = file_dict
                
                documents_data.append(doc_dict)
        
        # Convert project to dict using schema (includes all fields)
        from app.schemas.project import ProjectResponse
        project_dict = ProjectResponse.model_validate(project).model_dump()
        # Add documents with file details to the project dict
        project_dict["documents"] = documents_data
        
        return project_dict

    def get_project_with_commitment_by_reference(
        self,
        project_reference_id: str,
        committed_by: Optional[str] = None,
    ) -> tuple[Project, Optional[Commitment]]:
        """
        Get project by reference ID and, if committed_by is provided,
        fetch the latest matching commitment for this project and committed_by.

        Only commitments in the following statuses are considered:
        - under_review
        - approved
        - funded
        - completed
        """
        project = self.get_project_by_reference_id(project_reference_id)

        commitment: Optional[Commitment] = None
        if committed_by:
            valid_statuses = ["under_review", "approved", "funded", "completed"]
            commitment = (
                self.db.query(Commitment)
                .filter(
                    Commitment.project_id == project_reference_id,
                    Commitment.committed_by == committed_by,
                    Commitment.status.in_(valid_statuses),
                )
                .order_by(Commitment.created_at.desc())
                .first()
            )

        return project, commitment
    
    def get_projects(
        self,
        skip: int = 0,
        limit: int = 100,
        organization_id: str = None,
        organization_type: str = None,
        status: str = None,
        visibility: str = None,
        state: str = None,
        user_id: str = None,
        search: str = None,
        states: str = None,
        categories: str = None,
        project_stage: str = None,
        municipality_credit_rating: str = None,
        funding_type: str = None,
        mode_of_implementation: str = None,
        ownership: str = None,
        min_funding_requirement: Decimal = None,
        max_funding_requirement: Decimal = None,
        min_commitment_gap: Decimal = None,
        max_commitment_gap: Decimal = None,
        min_total_project_cost: Decimal = None,
        max_total_project_cost: Decimal = None,
    ) -> Tuple[list[Project], int]:
        """Get list of projects with optional filters, ordered by most recent first"""
        query = self.db.query(Project)
        
        # Validate status if provided
        if status:
            self._validate_status(status)
            query = query.filter(Project.status == status)
        
        # Validate project_stage if provided
        if project_stage:
            self._validate_project_stage(project_stage)
            query = query.filter(Project.project_stage == project_stage)
        
        # Apply other filters
        if organization_id:
            query = query.filter(Project.organization_id == organization_id)
        if organization_type:
            query = query.filter(Project.organization_type == organization_type)
        if visibility:
            query = query.filter(Project.visibility == visibility)
        # Use states parameter if provided, otherwise fall back to state (for backward compatibility)
        state_filter = states if states else state
        if state_filter:
            query = query.filter(Project.state == state_filter)
        
        # Search by project_reference_id
        if search:
            query = query.filter(Project.project_reference_id.ilike(f"%{search}%"))
        
        # Category filter
        if categories:
            query = query.filter(Project.category == categories)
        
        # Municipality credit rating filter
        if municipality_credit_rating:
            query = query.filter(Project.municipality_credit_rating == municipality_credit_rating)
        
        # Funding type filter
        if funding_type:
            query = query.filter(Project.funding_type == funding_type)
        
        # Mode of implementation filter
        if mode_of_implementation:
            query = query.filter(Project.mode_of_implementation == mode_of_implementation)
        
        # Ownership filter
        if ownership:
            query = query.filter(Project.ownership == ownership)
        
        # Range filters for funding_requirement
        if min_funding_requirement is not None:
            query = query.filter(Project.funding_requirement >= min_funding_requirement)
        if max_funding_requirement is not None:
            query = query.filter(Project.funding_requirement <= max_funding_requirement)
        
        # Range filters for commitment_gap
        if min_commitment_gap is not None:
            query = query.filter(Project.commitment_gap >= min_commitment_gap)
        if max_commitment_gap is not None:
            query = query.filter(Project.commitment_gap <= max_commitment_gap)
        
        # Range filters for total_project_cost
        if min_total_project_cost is not None:
            query = query.filter(Project.total_project_cost >= min_total_project_cost)
        if max_total_project_cost is not None:
            query = query.filter(Project.total_project_cost <= max_total_project_cost)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply ordering: most recent first (created_at DESC), then by id DESC for consistent ordering
        projects = query.order_by(
            Project.created_at.desc(),
            Project.id.desc()
        ).offset(skip).limit(limit).all()

        # Optimize: Calculate favorite counts, user favorites, and committed amounts in minimal queries
        if projects:
            project_ref_ids = [project.project_reference_id for project in projects]
            
            if project_ref_ids:
                # Single query to get favorite counts for all projects
                favorite_counts = self.db.query(
                    ProjectFavorite.project_reference_id,
                    func.count(ProjectFavorite.project_reference_id).label('count')
                ).filter(
                    ProjectFavorite.project_reference_id.in_(project_ref_ids)
                ).group_by(ProjectFavorite.project_reference_id).all()
                
                # Create dictionary for O(1) lookup
                favorite_count_dict = {ref_id: count for ref_id, count in favorite_counts}
                
                # Get user's favorites in a single query (only if user_id provided)
                favorite_ref_set = set()
                if user_id:
                    user_favorites = self.db.query(ProjectFavorite.project_reference_id).filter(
                        ProjectFavorite.user_id == user_id,
                        ProjectFavorite.project_reference_id.in_(project_ref_ids)
                    ).all()
                    favorite_ref_set = {fav[0] for fav in user_favorites}
                
                # Single query to get total committed amounts for all projects
                # Only count commitments with valid statuses: under_review, approved, funded, completed
                valid_statuses = ["approved", "funded", "completed"]
                committed_amounts = (
                    self.db.query(
                        Commitment.project_id,
                        func.sum(Commitment.amount).label('total_amount')
                    )
                    .filter(
                        Commitment.project_id.in_(project_ref_ids),
                        Commitment.status.in_(valid_statuses)
                    )
                    .group_by(Commitment.project_id)
                    .all()
                )
                
                # Create dictionary for O(1) lookup
                committed_amount_dict = {
                    ref_id: total_amount for ref_id, total_amount in committed_amounts
                }
                
                # Annotate all projects in a single loop
                for project in projects:
                    # Always set favorite_count (default to 0 if no favorites)
                    setattr(project, "favorite_count", favorite_count_dict.get(project.project_reference_id, 0))
                    
                    # Set is_favorite only if user_id was provided
                    if user_id:
                        setattr(project, "is_favorite", project.project_reference_id in favorite_ref_set)
                    
                    # Set total_committed_amount (default to 0 if no commitments)
                    total_committed = committed_amount_dict.get(project.project_reference_id, Decimal("0"))
                    setattr(project, "total_committed_amount", total_committed)
            else:
                # Edge case: projects exist but no ref_ids (shouldn't happen, but handle gracefully)
                for project in projects:
                    setattr(project, "favorite_count", 0)
                    setattr(project, "total_committed_amount", Decimal("0"))
                    if user_id:
                        setattr(project, "is_favorite", False)
        else:
            # No projects to annotate
            pass
        
        logger.info(f"Retrieved {len(projects)} projects (total: {total}) with filters: status={status}, organization_id={organization_id}, organization_type={organization_type}, visibility={visibility}")
        
        return projects, total
    
    def update_project(self, project_id: int, project_data: ProjectUpdate) -> Project:
        """Update an existing project"""
        logger.info(f"Updating project {project_id}")
        
        try:
            project = self.get_project_by_id(project_id)
            
            # Validate status, stage, and visibility if provided
            update_dict = project_data.model_dump(exclude_unset=True)
            
            # Currency is backend-controlled - remove if frontend tries to change it
            if 'currency' in update_dict:
                logger.warning(f"Attempted to update currency for project {project_id}. Currency is backend-controlled and will be ignored.")
                del update_dict['currency']
            
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
    
    def approve_project(self, project_id: int, approved_by: str, admin_notes: str = None) -> Project:
        """Approve a project - sets status to 'active'. Can approve projects in 'pending_validation' status (including resubmitted ones)."""
        logger.info(f"Approving project {project_id} by {approved_by}")
        
        try:
            project = self.get_project_by_id(project_id)
            
            # Check if project is already approved/active
            if project.status == 'active':
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Project is already approved and active"
                )
            
            # Check if project is in a valid state for approval
            if project.status not in ['pending_validation']:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot approve a project with status '{project.status}'. Project must be in 'pending_validation' status."
                )
            
            # Update project status and approval fields
            project.status = 'active'
            project.approved_at = datetime.now()
            project.approved_by = approved_by
            if admin_notes:
                project.admin_notes = admin_notes
            
            self.db.commit()
            self.db.refresh(project)
            
            logger.info(f"Project {project_id} approved successfully by {approved_by}. Status set to 'active'")
            return project
            
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error approving project {project_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to approve project: {str(e)}"
            )
    
    def reject_project(self, project_id: int, reject_note: str, approved_by: str) -> Project:
        """Reject a project - sets status to 'rejected' and stores reject note"""
        logger.info(f"Rejecting project {project_id} by {approved_by}")
        
        try:
            project = self.get_project_by_id(project_id)
            
            # Check if project is already rejected
            if project.status == 'rejected':
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Project is already rejected"
                )
            
            # Check if project is already active
            if project.status == 'active':
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot reject an active project"
                )
            
            # Validate reject note is not empty
            if not reject_note or not reject_note.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Reject note is mandatory and cannot be empty"
                )
            
            # Update project status and reject note
            project.status = 'rejected'
            project.admin_notes = reject_note.strip()
            project.approved_by = approved_by
            
            # Create rejection history record
            rejection = ProjectRejectionHistory(
                project_id=project_id,
                rejected_by=approved_by,
                rejection_note=reject_note.strip()
            )
            self.db.add(rejection)
            
            self.db.commit()
            self.db.refresh(project)
            
            logger.info(f"Project {project_id} rejected successfully by {approved_by}. Status set to 'rejected' and rejection history created")
            return project
            
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error rejecting project {project_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reject project: {str(e)}"
            )
    
    def resubmit_project(self, project_id: int, project_data, updated_by: str = None) -> Project:
        """Resubmit a rejected project - updates project fields and changes status from 'rejected' to 'pending_validation'"""
        logger.info(f"Resubmitting project {project_id} by {updated_by}")
        
        try:
            project = self.get_project_by_id(project_id)
            
            # Validate project is in rejected status
            if project.status != 'rejected':
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot resubmit project with status '{project.status}'. Project must be in 'rejected' status."
                )
            
            # Get the latest rejection record for this project
            latest_rejection = self.db.query(ProjectRejectionHistory).filter(
                ProjectRejectionHistory.project_id == project_id
            ).order_by(ProjectRejectionHistory.rejected_at.desc()).first()
            
            if not latest_rejection:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Rejection history not found for this project"
                )
            
            # Extract resubmission_notes before processing update_dict (it's not a project field)
            resubmission_notes = getattr(project_data, 'resubmission_notes', None)
            
            # Validate and update project fields
            update_dict = project_data.model_dump(exclude_unset=True, exclude={'resubmission_notes'})
            
            # Remove fields that shouldn't be updated via resubmission
            if 'currency' in update_dict:
                logger.warning(f"Attempted to update currency for project {project_id}. Currency is backend-controlled and will be ignored.")
                del update_dict['currency']
            if 'status' in update_dict:
                logger.warning(f"Attempted to set status in resubmission for project {project_id}. Status will be set to 'pending_validation' automatically.")
                del update_dict['status']
            if 'project_reference_id' in update_dict:
                logger.warning(f"Attempted to update project_reference_id for project {project_id}. This field is immutable.")
                del update_dict['project_reference_id']
            
            # Validate stage and visibility if provided
            if 'project_stage' in update_dict:
                self._validate_project_stage(update_dict['project_stage'])
            if 'visibility' in update_dict:
                self._validate_visibility(update_dict['visibility'])
            
            # Preserve original rejection note in admin_notes
            original_rejection_note = project.admin_notes or ""
            
            # Update project fields
            for field, value in update_dict.items():
                setattr(project, field, value)
            
            # Change status to pending_validation
            project.status = 'pending_validation'
            
            # Reset approval fields (since it's being resubmitted)
            project.approved_at = None
            # Keep approved_by for audit trail (shows who rejected it)
            
            # Update admin_notes with resubmission info
            resubmission_info = []
            if resubmission_notes:
                resubmission_info.append(f"[RESUBMITTED on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by {updated_by}]: {resubmission_notes}")
            else:
                resubmission_info.append(f"[RESUBMITTED on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by {updated_by}]")
            
            # Preserve original rejection note and append resubmission info
            if original_rejection_note:
                project.admin_notes = f"{original_rejection_note}\n\n" + "\n".join(resubmission_info)
            else:
                project.admin_notes = "\n".join(resubmission_info)
            
            # Update updated_by and updated_at
            if updated_by:
                project.updated_by = updated_by
            project.updated_at = datetime.now()
            
            # Update rejection history record
            latest_rejection.resubmitted_at = datetime.now()
            
            self.db.commit()
            self.db.refresh(project)
            
            logger.info(f"Project {project_id} resubmitted successfully by {updated_by}. Status changed from 'rejected' to 'pending_validation'")
            return project
            
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error resubmitting project {project_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to resubmit project: {str(e)}"
            )
    
    def get_projects_commitments_summary(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[dict], int]:
        """
        Get aggregated summary of projects with their commitments.
        Returns unique projects from commitments table with aggregated data.
        """
        logger.info("Fetching projects commitments summary")
        
        try:
            # Main query with aggregations
            # Join with projects to get title
            query = (
                self.db.query(
                    Commitment.project_id,
                    Project.title.label("project_title"),
                    func.count(Commitment.id).label("total_commitments_count"),
                    # Status breakdown counts
                    func.sum(
                        case((Commitment.status == "under_review", 1), else_=0)
                    ).label("under_review_count"),
                    func.sum(
                        case((Commitment.status == "approved", 1), else_=0)
                    ).label("approved_count"),
                    func.sum(
                        case((Commitment.status == "rejected", 1), else_=0)
                    ).label("rejected_count"),
                    func.sum(
                        case((Commitment.status == "withdrawn", 1), else_=0)
                    ).label("withdrawn_count"),
                    # Total amount under review
                    func.sum(
                        case(
                            (Commitment.status == "under_review", Commitment.amount),
                            else_=Decimal("0")
                        )
                    ).label("total_amount_under_review"),
                    # Latest commitment date
                    func.max(Commitment.created_at).label("latest_commitment_date"),
                )
                .join(
                    Project,
                    Commitment.project_id == Project.project_reference_id,
                    isouter=False
                )
                .group_by(Commitment.project_id, Project.title)
            )
            
            # Get total count before pagination
            total = query.count()
            
            # Apply pagination and ordering (by latest commitment date desc)
            # Note: We need to use the alias for ordering since it's in the SELECT
            results = (
                query.order_by(func.max(Commitment.created_at).desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            
            # Fetch all valid commitments for all projects in one query (fix N+1 problem)
            # Only include commitments that are not rejected or withdrawn
            project_ids = [row.project_id for row in results]
            all_valid_commitments = (
                self.db.query(Commitment)
                .filter(
                    Commitment.project_id.in_(project_ids),
                    Commitment.status.in_(["under_review", "approved", "funded", "completed"]),
                )
                .all()
            )
            
            # Group commitments by project_id for efficient lookup
            commitments_by_project = {}
            for commitment in all_valid_commitments:
                if commitment.project_id not in commitments_by_project:
                    commitments_by_project[commitment.project_id] = []
                commitments_by_project[commitment.project_id].append(commitment)
            
            # Process results and find best deal for each project
            summary_list = []
            for row in results:
                project_ref_id = row.project_id
                
                # Find best deal: For loans, lowest interest rate; for others, highest amount
                # Use pre-fetched commitments (excluding rejected/withdrawn)
                project_commitments = commitments_by_project.get(project_ref_id, [])
                
                best_deal_amount = None
                best_deal_interest_rate = None
                best_deal_funding_mode = None
                
                if project_commitments:
                    # Filter loans with interest rate
                    loans_with_rate = [
                        c for c in project_commitments
                        if c.funding_mode == "loan" and c.interest_rate is not None
                    ]
                    
                    if loans_with_rate:
                        # Best deal = loan with lowest interest rate
                        best_commitment = min(
                            loans_with_rate,
                            key=lambda x: x.interest_rate
                        )
                        best_deal_amount = best_commitment.amount
                        best_deal_interest_rate = best_commitment.interest_rate
                        best_deal_funding_mode = best_commitment.funding_mode
                    else:
                        # No loans with rate, use highest amount commitment
                        best_commitment = max(
                            project_commitments,
                            key=lambda x: x.amount
                        )
                        best_deal_amount = best_commitment.amount
                        best_deal_interest_rate = best_commitment.interest_rate
                        best_deal_funding_mode = best_commitment.funding_mode
                
                summary_dict = {
                    "project_reference_id": project_ref_id,
                    "project_title": row.project_title,
                    "total_commitments_count": row.total_commitments_count or 0,
                    "status_under_review": int(row.under_review_count or 0),
                    "status_approved": int(row.approved_count or 0),
                    "status_rejected": int(row.rejected_count or 0),
                    "status_withdrawn": int(row.withdrawn_count or 0),
                    "total_amount_under_review": row.total_amount_under_review or Decimal("0"),
                    "best_deal_amount": best_deal_amount,
                    "best_deal_interest_rate": best_deal_interest_rate,
                    "best_deal_funding_mode": best_deal_funding_mode,
                    "latest_commitment_date": row.latest_commitment_date,
                }
                summary_list.append(summary_dict)
            
            logger.info(f"Retrieved {len(summary_list)} project commitments summaries (total: {total})")
            return summary_list, total
            
        except Exception as e:
            logger.error(f"Error fetching projects commitments summary: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch projects commitments summary: {str(e)}"
            )
    
    def get_fully_funded_projects(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Project], int]:
        """
        Get list of fully funded projects (status = 'funding_completed') with funding parameters:
        - Average interest_rate from approved commitments
        - Number of investors (count of approved commitments)
        """
        logger.info("Fetching fully funded projects with funding parameters")
        
        try:
            # Query projects with status 'funding_completed'
            query = self.db.query(Project).filter(
                Project.status == 'funding_completed'
            )
            
            # Get total count before pagination
            total = query.count()
            
            # Apply ordering: most recent first
            projects = query.order_by(
                Project.created_at.desc(),
                Project.id.desc()
            ).offset(skip).limit(limit).all()
            
            # For each project, calculate funding parameters from approved commitments
            for project in projects:
                # Query approved commitments for this project
                approved_commitments = (
                    self.db.query(Commitment)
                    .filter(
                        Commitment.project_id == project.project_reference_id,
                        Commitment.status == 'approved'
                    )
                    .all()
                )
                
                # Calculate average interest_rate (only from commitments that have interest_rate)
                interest_rates = [
                    c.interest_rate for c in approved_commitments
                    if c.interest_rate is not None
                ]
                
                if interest_rates:
                    # Use Decimal arithmetic for precision
                    total_rate = sum(interest_rates)
                    avg_interest_rate = total_rate / Decimal(str(len(interest_rates)))
                    # Round to 2 decimal places
                    setattr(project, "average_interest_rate", round(avg_interest_rate, 2))
                else:
                    setattr(project, "average_interest_rate", None)
                
                # Count number of investors (number of approved commitments)
                setattr(project, "number_of_investors", len(approved_commitments))
            
            logger.info(f"Retrieved {len(projects)} fully funded projects (total: {total})")
            return projects, total
            
        except Exception as e:
            logger.error(f"Error fetching fully funded projects: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch fully funded projects: {str(e)}"
            )
    
    def get_projects_funded_by_user(
        self,
        committed_by: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Project], int]:
        """
        Get all projects that have been funded by a specific user.
        
        This method joins the projects and commitments tables to find all projects
        where the user (committed_by) has made at least one commitment.
        For each project, it also fetches the latest commitment made by the user
        and attaches it to the project object so the commitment status can be included.
        
        Args:
            committed_by: User ID who has made commitments
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (list of projects with commitment data attached, total count)
        """
        logger.info(
            "Fetching projects funded by user %s, skip=%s, limit=%s",
            committed_by,
            skip,
            limit,
        )
        
        try:
            # Query to get distinct projects where user has made commitments
            # Join projects with commitments on project_reference_id
            query = (
                self.db.query(Project)
                .join(
                    Commitment,
                    Project.project_reference_id == Commitment.project_id
                )
                .filter(Commitment.committed_by == committed_by)
                .distinct()
            )
            
            # Get total count before pagination
            total = query.count()
            
            # Apply ordering: most recent first
            projects = (
                query.order_by(
                    Project.created_at.desc(),
                    Project.id.desc()
                )
                .offset(skip)
                .limit(limit)
                .all()
            )
            
            # For each project, fetch the latest commitment made by this user
            # and attach it to the project object for serialization
            for project in projects:
                latest_commitment = (
                    self.db.query(Commitment)
                    .filter(
                        Commitment.project_id == project.project_reference_id,
                        Commitment.committed_by == committed_by,
                    )
                    .order_by(Commitment.created_at.desc())
                    .first()
                )
                
                # Attach commitment to project object
                # This will be serialized by ProjectResponse schema which has a commitment field
                if latest_commitment:
                    setattr(project, "commitment", latest_commitment)
                else:
                    setattr(project, "commitment", None)
            
            logger.info(
                "Retrieved %s projects funded by user %s (total: %s)",
                len(projects),
                committed_by,
                total,
            )
            
            return projects, total
            
        except Exception as e:
            logger.error(
                "Error fetching projects funded by user %s: %s",
                committed_by,
                str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch projects funded by user: {str(e)}"
            )
    
    def get_distinct_states(self) -> List[str]:
        """Get all distinct states from projects table, ordered alphabetically."""
        try:
            distinct_states = (
                self.db.query(Project.state)
                .filter(Project.state.isnot(None))
                .filter(Project.state != "")
                .distinct()
                .order_by(Project.state)
                .all()
            )
            # Extract state values from tuples (query returns tuples when selecting single column)
            states = [state[0].strip() for state in distinct_states if state[0] and state[0].strip()]
            return states
        except Exception as e:
            logger.error(f"Error fetching distinct states: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch distinct states: {str(e)}"
            )
    
    def get_distinct_municipality_credit_ratings(self) -> List[str]:
        """Get all distinct municipality_credit_rating values from projects table, ordered alphabetically."""
        try:
            distinct_ratings = (
                self.db.query(Project.municipality_credit_rating)
                .filter(Project.municipality_credit_rating.isnot(None))
                .filter(Project.municipality_credit_rating != "")
                .distinct()
                .order_by(Project.municipality_credit_rating)
                .all()
            )
            # Extract rating values from tuples (query returns tuples when selecting single column)
            ratings = [rating[0].strip() for rating in distinct_ratings if rating[0] and rating[0].strip()]
            return ratings
        except Exception as e:
            logger.error(f"Error fetching distinct municipality credit ratings: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch distinct municipality credit ratings: {str(e)}"
            )
    
    def get_value_ranges(self) -> dict:
        """Get min and max ranges for funding_requirement, commitment_gap, and total_project_cost fields."""
        try:
            # Get max funding_requirement (min is always 0)
            max_funding_requirement_result = (
                self.db.query(func.max(Project.funding_requirement))
                .scalar()
            )
            max_funding_requirement = Decimal('0') if max_funding_requirement_result is None else max_funding_requirement_result
            
            # Get max commitment_gap where not null (min is always 0)
            max_commitment_gap_result = (
                self.db.query(func.max(Project.commitment_gap))
                .filter(Project.commitment_gap.isnot(None))
                .scalar()
            )
            max_commitment_gap = Decimal('0') if max_commitment_gap_result is None else max_commitment_gap_result
            
            # Get max total_project_cost where not null (min is always 0)
            max_total_project_cost_result = (
                self.db.query(func.max(Project.total_project_cost))
                .filter(Project.total_project_cost.isnot(None))
                .scalar()
            )
            max_total_project_cost = Decimal('0') if max_total_project_cost_result is None else max_total_project_cost_result
            
            return {
                "min_funding_requirement": Decimal('0'),
                "max_funding_requirement": max_funding_requirement,
                "min_commitment_gap": Decimal('0'),
                "max_commitment_gap": max_commitment_gap,
                "min_total_project_cost": Decimal('0'),
                "max_total_project_cost": max_total_project_cost,
            }
        except Exception as e:
            logger.error(f"Error fetching value ranges: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch value ranges: {str(e)}"
            )

