from typing import Optional, List, Union
from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, File, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user, CurrentUser
from app.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    QuestionListResponse,
)
from app.services.question_service import QuestionService

router = APIRouter()


def _normalize_files(files: Union[UploadFile, List[UploadFile], None]) -> Optional[List[UploadFile]]:
    """Normalize files parameter to always be a list or None."""
    if files is None:
        return None
    # Check if it's not a list/sequence (but not a string)
    # This handles both single UploadFile and list of UploadFiles
    if not isinstance(files, (list, tuple)):
        return [files]
    # Ensure it's a list (not tuple)
    return list(files) if isinstance(files, tuple) else files


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_question(
    question_data: QuestionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new question for a project.
    
    User is automatically extracted from JWT token in Authorization header
    or from user_id header (fallback for backward compatibility).
    """
    try:
        service = QuestionService(db)
        question = service.create_question(question_data, user_id=current_user.user_id)
        question_response = QuestionResponse.model_validate(question)
        return {
            "status": "success",
            "message": "Question created successfully",
            "data": question_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create question: {str(exc)}",
        )


@router.get(
    "/", response_model=QuestionListResponse, status_code=status.HTTP_200_OK
)
def list_questions(
    project_id: str | None = Query(None, description="Project reference ID to filter questions"),
    organization_id: str | None = Query(None, description="Organization ID to filter questions"),
    status_filter: str
    | None = Query(None, description="Filter by question status"),
    category: str | None = Query(None, description="Filter by category"),
    priority: str | None = Query(None, description="Filter by priority"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of records"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List questions with optional filters and pagination.
    
    Can filter by project_id (project_reference_id) and/or organization_id.
    At least one of project_id or organization_id should be provided.
    """
    # Validate that at least one filter is provided
    if not project_id and not organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of project_id or organization_id must be provided",
        )
    
    try:
        service = QuestionService(db)
        questions, total = service.list_questions(
            project_id=project_id,
            organization_id=organization_id,
            status_filter=status_filter,
            category=category,
            priority=priority,
            skip=skip,
            limit=limit,
        )
        questions_response = [
            QuestionResponse.model_validate(question) for question in questions
        ]
        return {
            "status": "success",
            "message": "Questions fetched successfully",
            "data": questions_response,
            "total": total,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch questions: {str(exc)}",
        )


@router.get(
    "/{question_id}", response_model=dict, status_code=status.HTTP_200_OK
)
def get_question(
    question_id: int,
    project_id: str = Query(..., description="Project reference ID this question belongs to"),
    db: Session = Depends(get_db),
):
    """
    Get a single question (and its answer, if any) for a given project.
    
    The response includes all documents associated with the answer (if any).
    Each document includes full file metadata.
    """
    try:
        service = QuestionService(db)
        question = service.get_question(project_id=project_id, question_id=question_id)
        question_response = QuestionResponse.model_validate(question)
        return {
            "status": "success",
            "message": "Question fetched successfully",
            "data": question_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch question: {str(exc)}",
        )


@router.put(
    "/{question_id}", response_model=dict, status_code=status.HTTP_200_OK
)
def update_question(
    question_id: int,
    question_data: QuestionUpdate,
    project_id: str = Query(..., description="Project reference ID this question belongs to"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing question.
    """
    try:
        service = QuestionService(db)
        question = service.update_question(
            project_id=project_id, question_id=question_id, data=question_data, user_id=current_user.user_id
        )
        question_response = QuestionResponse.model_validate(question)
        return {
            "status": "success",
            "message": "Question updated successfully",
            "data": question_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update question: {str(exc)}",
        )


@router.post(
    "/{question_id}/answer", response_model=dict, status_code=status.HTTP_201_CREATED
)
def answer_question(
    question_id: int,
    reply_text: str = Form(..., description="Answer text provided by municipality"),
    project_id: str = Query(..., description="Project reference ID this question belongs to"),
    organization_id: Optional[str] = Query(None, description="Organization ID (auto-fetched from project if not provided and files are uploaded)"),
    files: Union[UploadFile, List[UploadFile], None] = File(None, description="Optional file(s) to upload (single file or list)"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Answer a question. Enforces a single answer per question.
    
    **User Identification:**
    - User is automatically extracted from JWT token in Authorization header
    - Falls back to user_id header for backward compatibility
    
    **Document Upload:**
    - Documents are optional
    - If provided, documents are saved to: Additional/{project_reference_id}/QandA/{question_reply_id}/
    - organization_id is automatically fetched from project if not provided and files are uploaded
    - Can accept a single file or a list of files
    """
    try:
        # Normalize files to always be a list or None
        normalized_files = _normalize_files(files)
        
        
        service = QuestionService(db)
        question = service.answer_question(
            project_id=project_id,
            question_id=question_id,
            replied_by_user_id=current_user.user_id,  # ✅ From auth context
            reply_text=reply_text,
            organization_id=organization_id,
            files=normalized_files,
        )
        question_response = QuestionResponse.model_validate(question)
        return {
            "status": "success",
            "message": "Question answered successfully",
            "data": question_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to answer question: {str(exc)}",
        )


@router.put(
    "/{question_id}/answer", response_model=dict, status_code=status.HTTP_200_OK
)
def update_answer(
    question_id: int,
    reply_text: str = Form(..., description="Updated answer text provided by municipality"),
    project_id: str = Query(..., description="Project reference ID this question belongs to"),
    organization_id: Optional[str] = Query(None, description="Organization ID (auto-fetched from project if not provided and files are uploaded)"),
    files: Union[UploadFile, List[UploadFile], None] = File(None, description="Optional file(s) to upload (replaces existing documents, single file or list)"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing answer for a question.
    
    **User Identification:**
    - User is automatically extracted from JWT token in Authorization header
    - Falls back to user_id header for backward compatibility
    
    **Document Update:**
    - Documents are optional
    - If files are provided, existing documents are deleted and replaced with new ones
    - If files is None (not provided), existing documents remain unchanged
    - If files is an empty list, all existing documents are removed
    - organization_id is automatically fetched from project if not provided and files are uploaded
    - Can accept a single file or a list of files
    - Documents are saved to: Additional/{project_reference_id}/QandA/{question_reply_id}/
    """
    try:
        # Normalize files to always be a list or None
        normalized_files = _normalize_files(files)
        
        service = QuestionService(db)
        question = service.update_answer(
            project_id=project_id,
            question_id=question_id,
            replied_by_user_id=current_user.user_id,  # ✅ From auth context
            reply_text=reply_text,
            organization_id=organization_id,
            files=normalized_files,
        )
        question_response = QuestionResponse.model_validate(question)
        return {
            "status": "success",
            "message": "Answer updated successfully",
            "data": question_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update answer: {str(exc)}",
        )


@router.delete(
    "/{question_id}", status_code=status.HTTP_200_OK
)
def delete_question(
    question_id: int,
    project_id: str = Query(..., description="Project reference ID this question belongs to"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a question written by the same person.

    **User Identification:**
    - User is automatically extracted from JWT token in Authorization header
    - Falls back to user_id header for backward compatibility
    - Only the user who created the question can delete it

    If the question has an answer, it is also deleted automatically
    via cascade.
    """
    try:
        service = QuestionService(db)
        service.delete_question(
            project_id=project_id,
            question_id=question_id,
            requested_by=current_user.user_id,  # ✅ From auth context
        )
        return {
            "status": "success",
            "message": "Question deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete question: {str(exc)}",
        )


@router.delete(
    "/{question_id}/answer", status_code=status.HTTP_200_OK
)
def delete_answer(
    question_id: int,
    project_id: str = Query(..., description="Project reference ID this question belongs to"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete the answer for a question.

    **User Identification:**
    - User is automatically extracted from JWT token in Authorization header
    - Falls back to user_id header for backward compatibility

    After deletion, the question status is set back to 'open'.
    """
    try:
        service = QuestionService(db)
        question = service.delete_answer(
            project_id=project_id,
            question_id=question_id,
            replied_by_user_id=current_user.user_id,  # ✅ From auth context
        )
        question_response = QuestionResponse.model_validate(question)
        return {
            "status": "success",
            "message": "Answer deleted successfully",
            "data": question_response,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete answer: {str(exc)}",
        )



