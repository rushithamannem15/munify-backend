from typing import Tuple, List
from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.logging import get_logger
from app.models.project import Project
from app.models.commitment import Commitment
from app.models.commitment_history import CommitmentHistory
from app.schemas.commitment import (
    CommitmentCreate,
    CommitmentUpdate,
)


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

    def create_commitment(self, payload: CommitmentCreate) -> Commitment:
        """Create a new commitment for a project. Initial status: under_review."""
        logger.info(
            "Creating commitment for project %s by %s",
            payload.project_reference_id,
            payload.committed_by,
        )
        try:
            project = self._get_project_by_reference_id(payload.project_reference_id)

            data = payload.model_dump(exclude_unset=True)

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
                actor=payload.created_by or payload.committed_by,
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
        self, commitment_id: int, payload: CommitmentUpdate
    ) -> Commitment:
        """Update commitment details while in under_review status."""
        logger.info("Updating commitment %s", commitment_id)
        try:
            commitment = self._get_commitment_or_404(commitment_id)
            self._ensure_modifiable(commitment)

            update_data = payload.model_dump(exclude_unset=True)

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
                actor=payload.updated_by or commitment.committed_by,
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

    def withdraw_commitment(self, commitment_id: int, actor: str | None) -> Commitment:
        """Withdraw commitment while in under_review status."""
        logger.info("Withdrawing commitment %s", commitment_id)
        try:
            commitment = self._get_commitment_or_404(commitment_id)
            self._ensure_modifiable(commitment)

            self._ensure_transition_allowed(commitment.status, "withdrawn")
            commitment.status = "withdrawn"
            commitment.updated_at = datetime.now()
            if actor:
                commitment.updated_by = actor

            self._create_history_snapshot(
                commitment=commitment,
                action="withdrawn",
                actor=actor or commitment.committed_by,
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
        approved_by: str,
        approval_notes: str | None = None,
    ) -> Commitment:
        """Approve a commitment - status: under_review -> approved."""
        logger.info("Approving commitment %s by %s", commitment_id, approved_by)
        try:
            commitment = self._get_commitment_or_404(commitment_id)

            if commitment.status != "under_review":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only commitments in 'under_review' status can be approved",
                )

            self._ensure_transition_allowed(commitment.status, "approved")

            commitment.status = "approved"
            commitment.approved_by = approved_by
            commitment.approved_at = datetime.now()
            if approval_notes:
                commitment.rejection_notes = approval_notes
            commitment.updated_by = approved_by
            commitment.updated_at = datetime.now()

            self._create_history_snapshot(
                commitment=commitment,
                action="approved",
                actor=approved_by,
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
        approved_by: str,
        rejection_reason: str,
        rejection_notes: str | None = None,
    ) -> Commitment:
        """Reject a commitment - status: under_review -> rejected."""
        logger.info("Rejecting commitment %s by %s", commitment_id, approved_by)
        try:
            commitment = self._get_commitment_or_404(commitment_id)

            if commitment.status != "under_review":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only commitments in 'under_review' status can be rejected",
                )

            self._ensure_transition_allowed(commitment.status, "rejected")

            commitment.status = "rejected"
            commitment.approved_by = approved_by
            commitment.rejection_reason = rejection_reason
            commitment.rejection_notes = rejection_notes
            commitment.updated_by = approved_by
            commitment.updated_at = datetime.now()

            self._create_history_snapshot(
                commitment=commitment,
                action="rejected",
                actor=approved_by,
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

    def mark_funded(self, commitment_id: int, actor: str | None) -> Commitment:
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
            if actor:
                commitment.updated_by = actor
            commitment.updated_at = datetime.now()

            self._create_history_snapshot(
                commitment=commitment,
                action="funded",
                actor=actor or commitment.approved_by,
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

    def mark_completed(self, commitment_id: int, actor: str | None) -> Commitment:
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
            if actor:
                commitment.updated_by = actor
            commitment.updated_at = datetime.now()

            self._create_history_snapshot(
                commitment=commitment,
                action="completed",
                actor=actor or commitment.approved_by,
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



