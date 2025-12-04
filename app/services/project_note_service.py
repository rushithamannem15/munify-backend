from typing import List, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.project_note import ProjectNote
from app.models.project import Project
from app.schemas.project_note import ProjectNoteCreate
from app.core.logging import get_logger

logger = get_logger("services.project_note")


class ProjectNoteService:
    def __init__(self, db: Session):
        self.db = db

    def _validate_project_exists(self, project_reference_id: str) -> Project:
        """Validate that project exists by project_reference_id"""
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

    def create_project_note(self, note_data: ProjectNoteCreate) -> ProjectNote:
        """Create a new project note"""
        logger.info(
            f"Creating project note for project {note_data.project_reference_id}, org {note_data.organization_id}"
        )

        try:
            # Ensure project exists (by reference id)
            self._validate_project_exists(note_data.project_reference_id)

            note_dict = note_data.model_dump(exclude_unset=True)
            note = ProjectNote(**note_dict)
            self.db.add(note)
            self.db.commit()
            self.db.refresh(note)

            logger.info(f"Project note {note.id} created successfully")
            return note

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating project note: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create project note: {str(e)}",
            )

    def get_project_notes(
        self, organization_id: str, project_reference_id: str
    ) -> Tuple[List[ProjectNote], int]:
        """Get list of project notes for given organization and project_reference_id"""
        query = self.db.query(ProjectNote).filter(
            ProjectNote.organization_id == organization_id,
            ProjectNote.project_reference_id == project_reference_id,
        )

        total = query.count()
        notes = (
            query.order_by(
                ProjectNote.created_at.desc(),
                ProjectNote.id.desc(),
            ).all()
        )

        return notes, total


