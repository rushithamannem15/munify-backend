from typing import Optional, Tuple, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.logging import get_logger
from app.models.project import Project
from app.models.question import Question, QuestionReply
from app.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionAnswerCreate,
)

logger = get_logger("services.question")


class QuestionService:
    def __init__(self, db: Session):
        self.db = db

    def _validate_project_exists(self, project_id: str) -> Project:
        """Validate that project exists for the given project_reference_id."""
        project = (
            self.db.query(Project)
            .filter(Project.project_reference_id == project_id)
            .first()
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with reference ID '{project_id}' not found",
            )
        return project

    def _validate_question_status_for_answer(self, question: Question) -> None:
        """Ensure question is in a state that can be answered."""
        if question.status in ("closed",):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot answer a question in '{question.status}' status",
            )

    def create_question(self, data: QuestionCreate) -> Question:
        """Create a new question for a project."""
        logger.info(
            "Creating question for project %s by %s",
            data.project_id,
            data.asked_by,
        )

        try:
            # Validate project exists
            self._validate_project_exists(data.project_id)

            question_dict = data.model_dump(exclude_unset=True)
            # Ensure default values consistent with DB defaults
            if "status" not in question_dict or question_dict["status"] is None:
                question_dict["status"] = "open"
            if "is_public" not in question_dict or question_dict["is_public"] is None:
                question_dict["is_public"] = True
            if "priority" not in question_dict or question_dict["priority"] is None:
                question_dict["priority"] = "normal"

            question = Question(**question_dict)
            self.db.add(question)
            self.db.commit()
            self.db.refresh(question)

            logger.info("Question %s created successfully", question.id)
            return question
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            logger.error("Error creating question: %s", str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create question: {str(exc)}",
            )

    def list_questions(
        self,
        project_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Question], int]:
        """List questions with optional filters and pagination.
        
        Can filter by project_id (project_reference_id) and/or organization_id.
        If project_id is provided, validates that the project exists.
        """
        # Validate project exists if project_id is provided
        if project_id:
            self._validate_project_exists(project_id)

        # Start building query with join to Project if organization_id filter is needed
        if organization_id:
            query = (
                self.db.query(Question)
                .join(Project, Question.project_id == Project.project_reference_id)
                .options(joinedload(Question.answer))
                .filter(Project.organization_id == organization_id)
            )
        else:
            query = (
                self.db.query(Question)
                .options(joinedload(Question.answer))
            )

        # Apply project_id filter if provided
        if project_id:
            query = query.filter(Question.project_id == project_id)

        # Apply other filters
        if status_filter:
            query = query.filter(Question.status == status_filter)
        if category:
            query = query.filter(Question.category == category)
        if priority:
            query = query.filter(Question.priority == priority)

        total = query.count()

        questions = (
            query.order_by(Question.created_at.desc(), Question.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return questions, total

    def get_question(self, project_id: str, question_id: int) -> Question:
        """Get a single question for a project, including its answer."""
        self._validate_project_exists(project_id)

        question = (
            self.db.query(Question)
            .options(joinedload(Question.answer))
            .filter(Question.id == question_id, Question.project_id == project_id)
            .first()
        )
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID {question_id} not found for project '{project_id}'",
            )
        return question

    def update_question(
        self,
        project_id: str,
        question_id: int,
        data: QuestionUpdate,
    ) -> Question:
        """Update question fields (e.g., text, category, priority, status).

        If the question already has an answer, modification is not allowed.
        """
        question = self.get_question(project_id, question_id)

        if question.answer:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot modify question because it already has an answer",
            )

        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(question, field, value)

        try:
            self.db.commit()
            self.db.refresh(question)
            return question
        except Exception as exc:
            self.db.rollback()
            logger.error("Error updating question %s: %s", question_id, str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update question: {str(exc)}",
            )

    def answer_question(
        self,
        project_id: str,
        question_id: int,
        replied_by_user_id: str,
        data: QuestionAnswerCreate,
    ) -> Question:
        """
        Create an answer for a question.

        Enforces one answer per question; if an answer already exists, returns 409.
        """
        question = self.get_question(project_id, question_id)
        self._validate_question_status_for_answer(question)

        if question.answer:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Question already has an answer",
            )

        try:
            answer_dict = data.model_dump(exclude_unset=True)
            answer = QuestionReply(
                question_id=question.id,
                replied_by_user_id=replied_by_user_id,
                **answer_dict,
            )
            self.db.add(answer)

            # Update question status to answered
            question.status = "answered"

            self.db.commit()
            self.db.refresh(question)
            # Ensure answer relationship is loaded
            self.db.refresh(answer)
            return question
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            logger.error(
                "Error creating answer for question %s: %s", question_id, str(exc)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to answer question: {str(exc)}",
            )

    def update_answer(
        self,
        project_id: str,
        question_id: int,
        replied_by_user_id: str,
        data: QuestionAnswerCreate,
    ) -> Question:
        """Update existing answer for a question."""
        question = self.get_question(project_id, question_id)
        if not question.answer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Answer not found for this question",
            )

        answer = question.answer

        # Optionally, enforce that only the same user can update
        if replied_by_user_id != answer.replied_by_user_id:
            logger.warning(
                "User %s attempted to update answer %s owned by %s",
                replied_by_user_id,
                answer.id,
                answer.replied_by_user_id,
            )

        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(answer, field, value)

        try:
            self.db.commit()
            self.db.refresh(question)
            return question
        except Exception as exc:
            self.db.rollback()
            logger.error(
                "Error updating answer for question %s: %s", question_id, str(exc)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update answer: {str(exc)}",
            )

    def delete_question(
        self,
        project_id: str,
        question_id: int,
        requested_by: str,
    ) -> None:
        """
        Delete a question written by the same person.

        If the question has an answer, deletion is not allowed
        (caller must delete the answer first).
        """
        question = self.get_question(project_id, question_id)

        # Only the author of the question can delete it
        if question.asked_by != requested_by:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the user who asked the question can delete it",
            )

        # If answer exists, do not allow deletion until answer is removed
        if question.answer:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete question because it already has an answer. Delete the answer first.",
            )

        try:
            self.db.delete(question)
            self.db.commit()
            logger.info(
                "Question %s for project %s deleted by %s",
                question_id,
                project_id,
                requested_by,
            )
        except Exception as exc:
            self.db.rollback()
            logger.error(
                "Error deleting question %s for project %s: %s",
                question_id,
                project_id,
                str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete question: {str(exc)}",
            )

    def delete_answer(
        self,
        project_id: str,
        question_id: int,
        replied_by_user_id: str,
    ) -> Question:
        """
        Delete the answer for a question.

        After deletion, the question status is set back to 'open'.
        """
        question = self.get_question(project_id, question_id)

        if not question.answer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Answer not found for this question",
            )

        answer = question.answer

        # Optionally enforce that only the same user can delete their answer
        if replied_by_user_id != answer.replied_by_user_id:
            logger.warning(
                "User %s attempted to delete answer %s owned by %s",
                replied_by_user_id,
                answer.id,
                answer.replied_by_user_id,
            )

        try:
            self.db.delete(answer)
            # Reset question status back to open
            question.status = "open"

            self.db.commit()
            self.db.refresh(question)
            return question
        except Exception as exc:
            self.db.rollback()
            logger.error(
                "Error deleting answer for question %s: %s",
                question_id,
                str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete answer: {str(exc)}",
            )


