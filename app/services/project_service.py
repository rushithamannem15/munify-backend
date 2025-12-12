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

    def get_project_with_commitment_by_reference(
        self,
        project_reference_id: str,
        committed_by: Optional[str] = None,
    ) -> tuple[Project, Optional[Commitment]]:
        """
        Get project by reference ID and, if committed_by is provided,
        fetch the latest matching commitment for this project and committed_by.
        """
        project = self.get_project_by_reference_id(project_reference_id)

        commitment: Optional[Commitment] = None
        if committed_by:
            commitment = (
                self.db.query(Commitment)
                .filter(
                    Commitment.project_id == project_reference_id,
                    Commitment.committed_by == committed_by,
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
        user_id: str = None,
    ) -> Tuple[list[Project], int]:
        """Get list of projects with optional filters, ordered by most recent first"""
        query = self.db.query(Project)
        
        # Validate status if provided
        if status:
            self._validate_status(status)
            query = query.filter(Project.status == status)
        
        # Apply other filters
        if organization_id:
            query = query.filter(Project.organization_id == organization_id)
        if organization_type:
            query = query.filter(Project.organization_type == organization_type)
        if visibility:
            query = query.filter(Project.visibility == visibility)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply ordering: most recent first (created_at DESC), then by id DESC for consistent ordering
        projects = query.order_by(
            Project.created_at.desc(),
            Project.id.desc()
        ).offset(skip).limit(limit).all()

        # Optimize: Calculate favorite counts and user favorites in minimal queries
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
                
                # Annotate all projects in a single loop
                for project in projects:
                    # Always set favorite_count (default to 0 if no favorites)
                    setattr(project, "favorite_count", favorite_count_dict.get(project.project_reference_id, 0))
                    
                    # Set is_favorite only if user_id was provided
                    if user_id:
                        setattr(project, "is_favorite", project.project_reference_id in favorite_ref_set)
            else:
                # Edge case: projects exist but no ref_ids (shouldn't happen, but handle gracefully)
                for project in projects:
                    setattr(project, "favorite_count", 0)
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
            
            # Process results and find best deal for each project
            summary_list = []
            for row in results:
                project_ref_id = row.project_id
                
                # Find best deal: For loans, lowest interest rate; for others, highest amount
                # Query all commitments for this project to find best deal
                all_commitments = (
                    self.db.query(Commitment)
                    .filter(Commitment.project_id == project_ref_id)
                    .all()
                )
                
                # Find best deal: For loans, lowest interest rate; for others, highest amount
                best_deal_amount = None
                best_deal_interest_rate = None
                best_deal_funding_mode = None
                
                if all_commitments:
                    # Filter loans with interest rate
                    loans_with_rate = [
                        c for c in all_commitments
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
                            all_commitments,
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

