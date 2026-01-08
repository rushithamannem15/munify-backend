from typing import Tuple, List
from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.core.logging import get_logger
from app.models.project import Project
from app.models.commitment import Commitment
from app.models.commitment_history import CommitmentHistory
from app.schemas.commitment import (
    CommitmentCreate,
    CommitmentUpdate,
)
from app.services.commitment_document_service import CommitmentDocumentService
from app.schemas.commitment import CommitmentResponse


logger = get_logger("services.commitment")


VALID_STATUSES = [
    "under_review",
    "approved",
    "rejected",
    "withdrawn",
    "funded",
    "completed",
]

ALLOWED_TRANSITIONS = {
    "under_review": {"approved", "rejected", "withdrawn"},
    "approved": {"funded"},
    "funded": {"completed"},
    "rejected": set(),
    "withdrawn": set(),
    "completed": set(),
}


class CommitmentService:
    def __init__(self, db: Session):
        self.db = db

    # ------------- Internal helpers -------------

    def _get_project_by_reference_id(self, project_reference_id: str) -> Project:
        project = (
            self.db.query(Project)
            .filter(Project.project_reference_id == project_reference_id)
            .first()
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with reference ID '{project_reference_id}' not found",
            )
        return project

    def _get_commitment_or_404(self, commitment_id: int) -> Commitment:
        commitment = (
            self.db.query(Commitment).filter(Commitment.id == commitment_id).first()
        )
        if not commitment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Commitment with ID {commitment_id} not found",
            )
        return commitment
    
    def get_commitment_with_documents(self, commitment_id: int) -> dict:
        """
        Get commitment by ID with associated documents and file details.
        
        This method joins perdix_mp_commitment_documents and perdix_mp_files tables
        to return complete file information for all documents linked to the commitment.
        
        Args:
            commitment_id: Commitment ID
            
        Returns:
            Dictionary containing commitment data and documents with file details
        """
        
        
        # Get commitment
        commitment = self._get_commitment_or_404(commitment_id)
        
        # Get documents with file details using CommitmentDocumentService
        documents_data = []
        document_service = CommitmentDocumentService(self.db)
        documents = document_service.get_commitment_documents(
            commitment_id=commitment_id
        )
        
        # Build documents response with file details
        for doc in documents:
            doc_dict = {
                "id": doc.id,
                "commitment_id": doc.commitment_id,
                "file_id": doc.file_id,
                "document_type": doc.document_type,
                "is_required": doc.is_required,
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
        
        # Convert commitment to dict using schema (includes all fields)
        commitment_dict = CommitmentResponse.model_validate(commitment).model_dump()
        # Add documents with file details to the commitment dict
        commitment_dict["documents"] = documents_data
        
        return commitment_dict

    def _validate_status_value(self, status_value: str):
        if status_value not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid commitment status. Must be one of: {', '.join(VALID_STATUSES)}",
            )

    def _ensure_transition_allowed(self, current_status: str, new_status: str):
        if current_status == new_status:
            return
        allowed = ALLOWED_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot change status from '{current_status}' to '{new_status}'",
            )

    def _ensure_modifiable(self, commitment: Commitment):
        """Lender can modify only while status is under_review."""
        if commitment.status != "under_review":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Commitment can only be modified while it is in 'under_review' status",
            )

    def _create_history_snapshot(
        self,
        commitment: Commitment,
        action: str,
        actor: str | None = None,
    ) -> CommitmentHistory:
        history = CommitmentHistory(
            commitment_id=commitment.id,
            project_id=commitment.project_id,
            organization_type=commitment.organization_type,
            organization_id=commitment.organization_id,
            committed_by=commitment.committed_by,
            amount=commitment.amount,
            funding_mode=commitment.funding_mode,
            interest_rate=commitment.interest_rate,
            tenure_months=commitment.tenure_months,
            terms_conditions_text=commitment.terms_conditions_text,
            status=commitment.status,
            action=action,
            created_by=actor,
            updated_by=actor,
        )
        self.db.add(history)
        return history

    # ------------- Public methods -------------

    def create_commitment(self, payload: CommitmentCreate, user_id: str = None) -> Commitment:
        """Create a new commitment for a project. Initial status: under_review."""
        logger.info(
            "Creating commitment for project %s by %s",
            payload.project_reference_id,
            user_id or payload.committed_by,
        )
        try:
            project = self._get_project_by_reference_id(payload.project_reference_id)

            data = payload.model_dump(exclude_unset=True)

            # Set created_by from auth context if provided
            if user_id:
                data['created_by'] = user_id
                # Remove created_by from request data if it was provided (should come from auth)
                data.pop('created_by', None)
                data['created_by'] = user_id

            # Map project_reference_id -> project_id column
            project_reference_id = data.pop("project_reference_id")

            # Normalize currency and numeric fields
            if "currency" not in data or data["currency"] is None:
                data["currency"] = "INR"

            amount = data.get("amount")
            if isinstance(amount, float):
                data["amount"] = Decimal(str(amount))

            # Initial status always under_review
            data["status"] = "under_review"

            commitment = Commitment(
                project_id=project.project_reference_id,
                **data,
            )

            # Ensure default tracking values
            if commitment.update_count is None:
                commitment.update_count = 0

            self.db.add(commitment)
            self.db.flush()  # Get commitment.id before history

            # History snapshot
            self._create_history_snapshot(
                commitment=commitment,
                action="created",
                actor=user_id or payload.created_by or payload.committed_by,
            )

            self.db.commit()
            self.db.refresh(commitment)

            logger.info("Commitment %s created successfully", commitment.id)
            return commitment

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            logger.error("Error creating commitment: %s", str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create commitment: {str(exc)}",
            )

    def update_commitment(
        self, commitment_id: int, payload: CommitmentUpdate, user_id: str = None
    ) -> Commitment:
        """Update commitment details while in under_review status."""
        logger.info("Updating commitment %s", commitment_id)
        try:
            commitment = self._get_commitment_or_404(commitment_id)
            self._ensure_modifiable(commitment)

            update_data = payload.model_dump(exclude_unset=True)
            
            # Set updated_by from auth context if provided
            if user_id:
                commitment.updated_by = user_id
                # Remove updated_by from request data if it was provided (should come from auth)
                update_data.pop('updated_by', None)

            # Normalize numeric fields if necessary
            amount = update_data.get("amount")
            if isinstance(amount, float):
                update_data["amount"] = Decimal(str(amount))

            for field, value in update_data.items():
                setattr(commitment, field, value)

            # Increment update_count
            commitment.update_count = (commitment.update_count or 0) + 1
            commitment.updated_at = datetime.now()

            self._create_history_snapshot(
                commitment=commitment,
                action="updated",
                actor=user_id or payload.updated_by or commitment.committed_by,
            )

            self.db.commit()
            self.db.refresh(commitment)

            logger.info("Commitment %s updated successfully", commitment.id)
            return commitment

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            logger.error("Error updating commitment %s: %s", commitment_id, str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update commitment: {str(exc)}",
            )

    def withdraw_commitment(self, commitment_id: int, user_id: str | None) -> Commitment:
        """Withdraw commitment while in under_review status."""
        logger.info("Withdrawing commitment %s", commitment_id)
        try:
            commitment = self._get_commitment_or_404(commitment_id)
            self._ensure_modifiable(commitment)

            self._ensure_transition_allowed(commitment.status, "withdrawn")
            commitment.status = "withdrawn"
            commitment.updated_at = datetime.now()
            if user_id:
                commitment.updated_by = user_id

            self._create_history_snapshot(
                commitment=commitment,
                action="withdrawn",
                actor=user_id or commitment.committed_by,
            )

            self.db.commit()
            self.db.refresh(commitment)

            logger.info("Commitment %s withdrawn successfully", commitment.id)
            return commitment

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            logger.error("Error withdrawing commitment %s: %s", commitment_id, str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to withdraw commitment: {str(exc)}",
            )

    def approve_commitment(
        self,
        commitment_id: int,
        user_id: str,
        approval_notes: str | None = None,
    ) -> Commitment:
        """Approve a commitment - status: under_review -> approved."""
        logger.info("Approving commitment %s by %s", commitment_id, user_id)
        try:
            commitment = self._get_commitment_or_404(commitment_id)

            if commitment.status != "under_review":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only commitments in 'under_review' status can be approved",
                )

            self._ensure_transition_allowed(commitment.status, "approved")

            # Get the project for validation
            project = self._get_project_by_reference_id(commitment.project_id)

            # Validation 1: Amount must be positive
            if commitment.amount <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Commitment amount must be greater than zero",
                )

            # Validation 2: Project status must be 'active'
            if project.status != "active":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot approve commitment for project with status '{project.status}'. Project must be 'active'",
                )

            # Validation 3: Check funding requirement - total approved + under_review commitments should not exceed funding_requirement
            # Note: This commitment is currently 'under_review', so it's already included in the total
            existing_commitments_total = (
                self.db.query(func.sum(Commitment.amount))
                .filter(
                    Commitment.project_id == commitment.project_id,
                    Commitment.status.in_(["approved", "under_review", "funded", "completed"]),
                )
                .scalar() or Decimal("0")
            )

            # Check if total commitments (including this one) exceed funding requirement
            if existing_commitments_total > project.commitment_gap:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Total commitments ({existing_commitments_total}) exceed the project funding requirement "
                           f"({project.commitment_gap}). Cannot approve this commitment.",
                )

            # Calculate project funding_raised BEFORE updating commitment status
            # Sum of all approved/funded/completed commitments (excluding current one)
            approved_commitments_total = (
                self.db.query(func.sum(Commitment.amount))
                .filter(
                    Commitment.project_id == commitment.project_id,
                    Commitment.status.in_(["approved", "funded", "completed"]),
                    Commitment.id != commitment.id,  # Exclude current commitment
                )
                .scalar() or Decimal("0")
            )
            
            # Update commitment status
            commitment.status = "approved"
            commitment.approved_by = user_id
            commitment.approved_at = datetime.now()
            if approval_notes:
                commitment.rejection_notes = approval_notes
            commitment.updated_by = user_id
            commitment.updated_at = datetime.now()

            # Update project funding_raised (sum of all approved commitments including this one)
            project.funding_raised = approved_commitments_total + commitment.amount
            project.updated_at = datetime.now()
            project.updated_by = user_id

            self._create_history_snapshot(
                commitment=commitment,
                action="approved",
                actor=user_id,
            )

            self.db.commit()
            self.db.refresh(commitment)

            logger.info("Commitment %s approved successfully", commitment.id)
            return commitment

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            logger.error("Error approving commitment %s: %s", commitment_id, str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to approve commitment: {str(exc)}",
            )

    def reject_commitment(
        self,
        commitment_id: int,
        user_id: str,
        rejection_reason: str,
        rejection_notes: str | None = None,
    ) -> Commitment:
        """Reject a commitment - status: under_review -> rejected."""
        logger.info("Rejecting commitment %s by %s", commitment_id, user_id)
        try:
            commitment = self._get_commitment_or_404(commitment_id)

            if commitment.status != "under_review":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only commitments in 'under_review' status can be rejected",
                )

            self._ensure_transition_allowed(commitment.status, "rejected")

            commitment.status = "rejected"
            commitment.approved_by = user_id
            commitment.rejection_reason = rejection_reason
            commitment.rejection_notes = rejection_notes
            commitment.updated_by = user_id
            commitment.updated_at = datetime.now()

            self._create_history_snapshot(
                commitment=commitment,
                action="rejected",
                actor=user_id,
            )

            self.db.commit()
            self.db.refresh(commitment)

            logger.info("Commitment %s rejected successfully", commitment.id)
            return commitment

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            logger.error("Error rejecting commitment %s: %s", commitment_id, str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reject commitment: {str(exc)}",
            )

    def mark_funded(self, commitment_id: int, user_id: str | None) -> Commitment:
        """Mark an approved commitment as funded."""
        logger.info("Marking commitment %s as funded", commitment_id)
        try:
            commitment = self._get_commitment_or_404(commitment_id)

            if commitment.status != "approved":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only commitments in 'approved' status can be marked as funded",
                )

            self._ensure_transition_allowed(commitment.status, "funded")
            commitment.status = "funded"
            if user_id:
                commitment.updated_by = user_id
            commitment.updated_at = datetime.now()

            self._create_history_snapshot(
                commitment=commitment,
                action="funded",
                actor=user_id or commitment.approved_by,
            )

            self.db.commit()
            self.db.refresh(commitment)

            logger.info("Commitment %s marked as funded", commitment.id)
            return commitment

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            logger.error("Error marking commitment %s as funded: %s", commitment_id, str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to mark commitment as funded: {str(exc)}",
            )

    def mark_completed(self, commitment_id: int, user_id: str | None) -> Commitment:
        """Mark a funded commitment as completed."""
        logger.info("Marking commitment %s as completed", commitment_id)
        try:
            commitment = self._get_commitment_or_404(commitment_id)

            if commitment.status != "funded":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only commitments in 'funded' status can be marked as completed",
                )

            self._ensure_transition_allowed(commitment.status, "completed")
            commitment.status = "completed"
            if user_id:
                commitment.updated_by = user_id
            commitment.updated_at = datetime.now()

            self._create_history_snapshot(
                commitment=commitment,
                action="completed",
                actor=user_id or commitment.approved_by,
            )

            self.db.commit()
            self.db.refresh(commitment)

            logger.info("Commitment %s marked as completed", commitment.id)
            return commitment

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            logger.error(
                "Error marking commitment %s as completed: %s", commitment_id, str(exc)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to mark commitment as completed: {str(exc)}",
            )

    def get_commitment_by_id(self, commitment_id: int) -> Commitment:
        return self._get_commitment_or_404(commitment_id)

    def list_commitments(
        self,
        skip: int = 0,
        limit: int = 100,
        project_reference_id: str | None = None,
        organization_id: str | None = None,
        organization_type: str | None = None,
        status_filter: str | None = None,
    ) -> Tuple[List[Commitment], int]:
        """List commitments with optional filters."""
        query = self.db.query(Commitment)

        if project_reference_id:
            query = query.filter(Commitment.project_id == project_reference_id)
        if organization_id:
            query = query.filter(Commitment.organization_id == organization_id)
        if organization_type:
            query = query.filter(Commitment.organization_type == organization_type)
        if status_filter:
            self._validate_status_value(status_filter)
            query = query.filter(Commitment.status == status_filter)

        total = query.count()
        commitments = (
            query.order_by(Commitment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        logger.info(
            "Retrieved %s commitments (total: %s) with filters project_reference_id=%s, organization_id=%s, organization_type=%s, status=%s",
            len(commitments),
            total,
            project_reference_id,
            organization_id,
            organization_type,
            status_filter,
        )

        return commitments, total

    def list_commitments_for_lender(
        self,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Commitment], int]:
        """List commitments for a specific lender organization."""
        query = self.db.query(Commitment).filter(
            Commitment.organization_id == organization_id
        )
        total = query.count()
        commitments = (
            query.order_by(Commitment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return commitments, total

    def get_commitment_history(
        self,
        commitment_id: int,
    ) -> List[CommitmentHistory]:
        """Return history entries for a commitment ordered by created_at asc."""
        _ = self._get_commitment_or_404(commitment_id)
        history = (
            self.db.query(CommitmentHistory)
            .filter(CommitmentHistory.commitment_id == commitment_id)
            .order_by(CommitmentHistory.created_at.asc())
            .all()
        )
        return history



