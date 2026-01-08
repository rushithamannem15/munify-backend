from sqlalchemy import Column, BigInteger, String, Text, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Question(Base):
    """
    Model for perdix_mp_questions
    """

    __tablename__ = "perdix_mp_questions"

    id = Column(BigInteger, primary_key=True, index=True)

    # Reference to project by project_reference_id
    project_id = Column(String(255), ForeignKey("perdix_mp_projects.project_reference_id"), nullable=False)

    asked_by = Column(String(255), nullable=False)
    question_text = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    attachments = Column(JSON, nullable=False, server_default="[]")

    status = Column(String(50), nullable=False, server_default="open")
    is_public = Column(Boolean, nullable=False, server_default="true")
    priority = Column(String(20), nullable=False, server_default="normal")

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(255), nullable=True)

    # Relationships
    answer = relationship(
        "QuestionReply",
        uselist=False,
        back_populates="question",
        cascade="all, delete-orphan",
    )


class QuestionReply(Base):
    """
    Model for perdix_mp_question_replies
    One reply per question is enforced at DB level via unique constraint on question_id.
    """

    __tablename__ = "perdix_mp_question_replies"

    id = Column(BigInteger, primary_key=True, index=True)

    question_id = Column(BigInteger, ForeignKey("perdix_mp_questions.id", ondelete="CASCADE"), nullable=False, unique=True)
    # Store user identifier as string (username/user_id) to match asked_by field in questions
    replied_by_user_id = Column(String(255), nullable=False)

    reply_text = Column(Text, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(255), nullable=True)

    # Relationships
    question = relationship("Question", back_populates="answer")
    documents = relationship(
        "QuestionReplyDocument",
        back_populates="question_reply",
        cascade="all, delete-orphan",
    )


