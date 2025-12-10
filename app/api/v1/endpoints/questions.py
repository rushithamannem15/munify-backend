from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionAnswerCreate,
    QuestionResponse,
    QuestionListResponse,
)
from app.services.question_service import QuestionService

router = APIRouter()


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_question(question_data: QuestionCreate, db: Session = Depends(get_db)):
    """
    Create a new question for a project.
    """
    try:
        service = QuestionService(db)
        question = service.create_question(question_data)
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
    db: Session = Depends(get_db),
):
    """
    Update an existing question.
    """
    try:
        service = QuestionService(db)
        question = service.update_question(
            project_id=project_id, question_id=question_id, data=question_data
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
    answer_data: QuestionAnswerCreate,
    project_id: str = Query(..., description="Project reference ID this question belongs to"),
    replied_by_user_id: str = Query(
        ..., description="User identifier (username or user ID) of the municipality user providing the answer"
    ),
    db: Session = Depends(get_db),
):
    """
    Answer a question. Enforces a single answer per question.
    """
    try:
        service = QuestionService(db)
        question = service.answer_question(
            project_id=project_id,
            question_id=question_id,
            replied_by_user_id=replied_by_user_id,
            data=answer_data,
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
    answer_data: QuestionAnswerCreate,
    project_id: str = Query(..., description="Project reference ID this question belongs to"),
    replied_by_user_id: str = Query(
        ..., description="User identifier (username or user ID) of the municipality user updating the answer"
    ),
    db: Session = Depends(get_db),
):
    """
    Update an existing answer for a question.
    """
    try:
        service = QuestionService(db)
        question = service.update_answer(
            project_id=project_id,
            question_id=question_id,
            replied_by_user_id=replied_by_user_id,
            data=answer_data,
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
    requested_by: str = Query(
        ..., description="Identifier of the user requesting deletion (must match asked_by)"
    ),
    db: Session = Depends(get_db),
):
    """
    Delete a question written by the same person.

    If the question has an answer, it is also deleted automatically
    via cascade.
    """
    try:
        service = QuestionService(db)
        service.delete_question(
            project_id=project_id,
            question_id=question_id,
            requested_by=requested_by,
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
    replied_by_user_id: str = Query(
        ..., description="User identifier (username or user ID) of the municipality user deleting the answer"
    ),
    db: Session = Depends(get_db),
):
    """
    Delete the answer for a question.

    After deletion, the question status is set back to 'open'.
    """
    try:
        service = QuestionService(db)
        question = service.delete_answer(
            project_id=project_id,
            question_id=question_id,
            replied_by_user_id=replied_by_user_id,
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



