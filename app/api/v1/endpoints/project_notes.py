from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.project_note import ProjectNoteCreate, ProjectNoteResponse
from app.services.project_note_service import ProjectNoteService

router = APIRouter()


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_project_note(note_data: ProjectNoteCreate, db: Session = Depends(get_db)):
    """Create a new project note"""
    try:
        service = ProjectNoteService(db)
        note = service.create_project_note(note_data)
        note_response = ProjectNoteResponse.model_validate(note)
        return {
            "status": "success",
            "message": "Project note created successfully",
            "data": note_response,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project note: {str(e)}",
        )


@router.get("/", response_model=dict, status_code=status.HTTP_200_OK)
def get_project_notes(
    organization_id: str = Query(..., description="Organization ID"),
    project_reference_id: str = Query(..., description="Project reference ID"),
    db: Session = Depends(get_db),
):
    """Get project notes for a given organization and project_reference_id"""
    try:
        service = ProjectNoteService(db)
        notes, total = service.get_project_notes(
            organization_id=organization_id,
            project_reference_id=project_reference_id,
        )
        notes_response = [ProjectNoteResponse.model_validate(note) for note in notes]
        return {
            "status": "success",
            "message": "Project notes fetched successfully",
            "data": notes_response,
            "total": total,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project notes: {str(e)}",
        )


